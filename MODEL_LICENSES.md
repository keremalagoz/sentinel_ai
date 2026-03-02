# Model Lisansları

Bu projede kullanılan model ağırlıkları ve model artefaktları, proje kod lisansından
bağımsızdır ve ilgili sağlayıcının lisans şartlarına tabidir.

## Kural

- `LICENSE` yalnızca proje kaynak kodu için geçerlidir.
- Model ağırlıkları için son söz upstream model lisansındadır.
- Proje lisansı, model sağlayıcısının verdiği hakları genişletmez veya daraltmaz.

## Referanslanan model kaynakları

### 1) Qwen 2.5 3B Instruct GGUF

- Kaynak URL:
  - `https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf`
- Referanslandığı dosyalar:
  - `docker/ollama/setup_model.sh`
  - `models/Modelfile.qwen2.5`

### 2) WhiteRabbitNeo V3 7B GGUF

- Kaynak URL:
  - `https://huggingface.co/bartowski/WhiteRabbitNeo_WhiteRabbitNeo-V3-7B-GGUF/resolve/main/WhiteRabbitNeo_WhiteRabbitNeo-V3-7B-Q4_K_M.gguf`
- Referanslandığı dosyalar:
  - `docker/ollama/setup_model.sh`
  - `docker/whiterabbitneo/setup_model.sh`
  - `models/Modelfile.whiterabbitneo`

## Dağıtım politikası

- Model ağırlıklarını repoda veya release artefaktında paylaşıyorsanız, ilgili modelin
  lisans metnini ayrıca eklemek zorundasınız.
- Model lisansı ticari kullanım, türev model üretimi veya yeniden dağıtım için kısıt
  getiriyorsa, bu kısıtlar aynen geçerlidir.

## Uyum kontrol listesi

Model dosyası eklemeden önce:

1. Hugging Face model kartındaki lisans alanını kontrol edin.
2. Gerekliyse ek şartları (AUP, kullanım politikası, atıf şartı) doğrulayın.
3. Release notlarına model lisansını ayrı başlıkta ekleyin.
