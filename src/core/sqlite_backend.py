"""SQLite Backend - Entity Storage and Execution History

Sprint 1 Week 1 Implementation
Locked Design: docs/sqlite_schema.md
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from contextlib import contextmanager
from pydantic import BaseModel


class EntityType:
    """Entity type constants"""
    HOST = "host"
    PORT = "port"
    SERVICE = "service"
    VULNERABILITY = "vulnerability"
    WEB_RESOURCE = "web_resource"
    DNS = "dns"
    CERTIFICATE = "certificate"
    CREDENTIAL = "credential"
    FILE = "file"


class RelationshipType:
    """Relationship type constants"""
    HAS_PORT = "has_port"
    HAS_SERVICE = "has_service"
    HAS_VULNERABILITY = "has_vulnerability"
    HAS_WEB_RESOURCE = "has_web_resource"
    RESOLVES_TO = "resolves_to"


class ExecutionStatus:
    """Tool execution status constants"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial"


class ParseStatus:
    """Parse status constants"""
    PARSED = "parsed"
    PARSE_FAILED = "parse_failed"
    EMPTY_OUTPUT = "empty_output"


class BaseEntity(BaseModel):
    """Base entity model - all entities inherit this"""
    id: str
    entity_type: str
    created_at: float
    updated_at: float
    confidence: float = 1.0
    data: Dict[str, Any]
    
    class Config:
        arbitrary_types_allowed = True


class ToolExecutionResult(BaseModel):
    """Tool execution result model"""
    execution_id: str
    tool_id: str
    stage_id: Optional[int] = None
    status: str  # ExecutionStatus
    parse_status: str  # ParseStatus
    raw_output: str
    started_at: float
    completed_at: float
    entities_created: int = 0
    error_message: Optional[str] = None


class SQLiteBackend:
    """
    SQLite backend for entity storage and execution history.
    
    Implementation of locked design from docs/sqlite_schema.md
    
    Features:
    - Hybrid schema (JSON blob + FK relationships)
    - Transaction support (atomic batch insert)
    - TTL & pruning
    - Checkpoint/restore
    """
    
    def __init__(self, db_path: str = "sentinel_state.db"):
        """
        Initialize SQLite backend.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Create database and tables if they don't exist"""
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row  # Enable dict-like row access
        
        cursor = self.connection.cursor()
        
        # Table 1: entities (JSON blob + metadata)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                confidence REAL DEFAULT 1.0,
                data JSON NOT NULL
            )
        """)
        
        # Indexes for query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_type ON entities(entity_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON entities(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_updated_at ON entities(updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_confidence ON entities(confidence)")
        
        # Table 2: entity_relationships (FK relationships)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entity_relationships (
                parent_id TEXT NOT NULL,
                child_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (parent_id, child_id, relationship_type),
                FOREIGN KEY (parent_id) REFERENCES entities(id) ON DELETE CASCADE,
                FOREIGN KEY (child_id) REFERENCES entities(id) ON DELETE CASCADE
            )
        """)
        
        # Indexes for bidirectional queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent ON entity_relationships(parent_id, relationship_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_child ON entity_relationships(child_id, relationship_type)")
        
        # Table 3: tool_executions (execution history)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_executions (
                execution_id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL,
                stage_id INTEGER,
                status TEXT NOT NULL,
                parse_status TEXT NOT NULL,
                raw_output TEXT,
                started_at REAL NOT NULL,
                completed_at REAL NOT NULL,
                entities_created INTEGER DEFAULT 0,
                error_message TEXT
            )
        """)
        
        # Indexes for execution history queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tool_id ON tool_executions(tool_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stage_id ON tool_executions(stage_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tool_executions(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_started_at ON tool_executions(started_at)")
        
        self.connection.commit()
    
    @contextmanager
    def transaction(self):
        """
        Transaction context manager for atomic operations.
        
        Usage:
            with backend.transaction():
                backend.insert_entity(entity1)
                backend.insert_entity(entity2)
                # All or nothing - rollback on exception
        """
        cursor = self.connection.cursor()
        try:
            cursor.execute("BEGIN")
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise e
    
    def insert_entity(self, entity: BaseEntity) -> None:
        """
        Insert a single entity.
        
        Args:
            entity: Entity to insert
            
        Note: Use add_entities_batch for multiple entities (atomic transaction)
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO entities 
            (id, entity_type, created_at, updated_at, confidence, data)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entity.id,
                entity.entity_type,
                entity.created_at,
                entity.updated_at,
                entity.confidence,
                json.dumps(entity.data)
            )
        )
        self.connection.commit()
    
    def add_entities_batch(self, entities: List[BaseEntity]) -> int:
        """
        Atomic batch insert with transaction.
        
        Args:
            entities: List of entities to insert
            
        Returns:
            Number of entities inserted
            
        Note: All entities inserted or none (rollback on exception)
        """
        with self.transaction():
            cursor = self.connection.cursor()
            
            for entity in entities:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO entities 
                    (id, entity_type, created_at, updated_at, confidence, data)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entity.id,
                        entity.entity_type,
                        entity.created_at,
                        entity.updated_at,
                        entity.confidence,
                        json.dumps(entity.data)
                    )
                )
        
        return len(entities)
    
    def get_entity(self, entity_id: str) -> Optional[BaseEntity]:
        """
        Get entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity if found, None otherwise
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM entities WHERE id = ?", (entity_id,))
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return BaseEntity(
            id=row["id"],
            entity_type=row["entity_type"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            confidence=row["confidence"],
            data=json.loads(row["data"])
        )
    
    def get_entities_by_type(self, entity_type: str) -> List[BaseEntity]:
        """
        Get all entities of a specific type.
        
        Args:
            entity_type: Entity type (host, port, service, etc.)
            
        Returns:
            List of entities
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM entities WHERE entity_type = ?", (entity_type,))
        rows = cursor.fetchall()
        
        entities = []
        for row in rows:
            entities.append(BaseEntity(
                id=row["id"],
                entity_type=row["entity_type"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                confidence=row["confidence"],
                data=json.loads(row["data"])
            ))
        
        return entities
    
    def add_relationship(self, parent_id: str, child_id: str, relationship_type: str) -> None:
        """
        Add entity relationship.
        
        Args:
            parent_id: Parent entity ID
            child_id: Child entity ID
            relationship_type: Relationship type (has_port, has_service, etc.)
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO entity_relationships 
            (parent_id, child_id, relationship_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (parent_id, child_id, relationship_type, time.time())
        )
        self.connection.commit()
    
    def get_children(self, parent_id: str, relationship_type: str) -> List[BaseEntity]:
        """
        Get child entities for a parent.
        
        Args:
            parent_id: Parent entity ID
            relationship_type: Relationship type filter
            
        Returns:
            List of child entities
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT e.* FROM entities e
            JOIN entity_relationships r ON r.child_id = e.id
            WHERE r.parent_id = ? AND r.relationship_type = ?
            """,
            (parent_id, relationship_type)
        )
        rows = cursor.fetchall()
        
        entities = []
        for row in rows:
            entities.append(BaseEntity(
                id=row["id"],
                entity_type=row["entity_type"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                confidence=row["confidence"],
                data=json.loads(row["data"])
            ))
        
        return entities
    
    def record_execution(self, result: ToolExecutionResult) -> None:
        """
        Record tool execution in history.
        
        Args:
            result: Tool execution result
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO tool_executions 
            (execution_id, tool_id, stage_id, status, parse_status, raw_output, 
             started_at, completed_at, entities_created, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.execution_id,
                result.tool_id,
                result.stage_id,
                result.status,
                result.parse_status,
                result.raw_output,
                result.started_at,
                result.completed_at,
                result.entities_created,
                result.error_message
            )
        )
        self.connection.commit()
    
    def has_tool_executed(self, tool_id: str) -> bool:
        """
        Check if tool has been executed.
        
        Args:
            tool_id: Tool ID
            
        Returns:
            True if tool executed successfully or partially
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT 1 FROM tool_executions 
            WHERE tool_id = ? AND status IN (?, ?)
            LIMIT 1
            """,
            (tool_id, ExecutionStatus.SUCCESS, ExecutionStatus.PARTIAL_SUCCESS)
        )
        return cursor.fetchone() is not None
    
    def get_last_execution(self, tool_id: str) -> Optional[ToolExecutionResult]:
        """
        Get last execution result for a tool.
        
        Args:
            tool_id: Tool ID
            
        Returns:
            Last execution result if found
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT * FROM tool_executions 
            WHERE tool_id = ? 
            ORDER BY completed_at DESC 
            LIMIT 1
            """,
            (tool_id,)
        )
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return ToolExecutionResult(
            execution_id=row["execution_id"],
            tool_id=row["tool_id"],
            stage_id=row["stage_id"],
            status=row["status"],
            parse_status=row["parse_status"],
            raw_output=row["raw_output"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            entities_created=row["entities_created"],
            error_message=row["error_message"]
        )
    
    def get_all_executions(self, tool_id: Optional[str] = None) -> List[ToolExecutionResult]:
        """
        Get all execution results, optionally filtered by tool.
        
        Args:
            tool_id: Optional tool ID to filter by
            
        Returns:
            List of execution results
        """
        cursor = self.connection.cursor()
        
        if tool_id:
            cursor.execute(
                """
                SELECT * FROM tool_executions 
                WHERE tool_id = ?
                ORDER BY started_at DESC
                """,
                (tool_id,)
            )
        else:
            cursor.execute(
                "SELECT * FROM tool_executions ORDER BY started_at DESC"
            )
        
        results = []
        for row in cursor.fetchall():
            results.append(ToolExecutionResult(
                execution_id=row["execution_id"],
                tool_id=row["tool_id"],
                stage_id=row["stage_id"],
                status=row["status"],
                parse_status=row["parse_status"],
                raw_output=row["raw_output"],
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                entities_created=row["entities_created"],
                error_message=row["error_message"]
            ))
        
        return results
    
    def prune_stale_entities(self, ttl_seconds: int = 3600) -> int:
        """
        Delete entities older than TTL.
        
        Args:
            ttl_seconds: Time to live in seconds (default 1 hour)
            
        Returns:
            Number of entities deleted
        """
        cutoff = time.time() - ttl_seconds
        
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM entities WHERE updated_at < ?", (cutoff,))
        deleted_count = cursor.rowcount
        
        self.connection.commit()
        return deleted_count
    
    def checkpoint(self, checkpoint_path: str) -> None:
        """
        Save current state to checkpoint file.
        
        Args:
            checkpoint_path: Path to checkpoint file
        """
        import shutil
        
        # Close connection to ensure all data is flushed
        self.connection.close()
        
        # Copy database file
        shutil.copy2(self.db_path, checkpoint_path)
        
        # Reconnect
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
    
    def restore(self, checkpoint_path: str) -> None:
        """
        Restore state from checkpoint file.
        
        Args:
            checkpoint_path: Path to checkpoint file
        """
        import shutil
        
        # Close current connection
        self.connection.close()
        
        # Restore checkpoint file
        shutil.copy2(checkpoint_path, self.db_path)
        
        # Reconnect
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics.
        
        Returns:
            Dict with entity counts by type and total executions
        """
        cursor = self.connection.cursor()
        
        # Entity counts by type
        cursor.execute("""
            SELECT entity_type, COUNT(*) as count 
            FROM entities 
            GROUP BY entity_type
        """)
        entity_counts = {row["entity_type"]: row["count"] for row in cursor.fetchall()}
        
        # Total executions
        cursor.execute("SELECT COUNT(*) as count FROM tool_executions")
        total_executions = cursor.fetchone()["count"]
        
        return {
            "entities": entity_counts,
            "total_executions": total_executions
        }
    
    def close(self) -> None:
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
