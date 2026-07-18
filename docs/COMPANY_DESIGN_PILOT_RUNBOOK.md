# Halı AI Mühendislik Demo Runbook

Durum: **PASS_WITH_RESTRICTIONS** — kısıtlı katalog referansı bağlıdır; onaylı eğitim verisi,
LoRA ve GPU üretim profili henüz bağlı değildir.

## 1. Sunum öncesi kontrol

```powershell
uv sync --all-extras
uv run carpet-designer doctor
uv run ruff check .
uv run mypy src
uv run pytest -q
```

Beklenti: test/lint/type kontrolleri geçmeli. GPU bulunmaması demo için engel değildir.

## 2. Sistemi açma

```powershell
uv run carpet-designer serve --port 8501
```

Tarayıcı: `http://localhost:8501`

## 3. Önerilen 8 dakikalık sunum akışı

1. **Yönetim Özeti** — modüler monolit ve kanıt zincirini açıklayın.
2. **Tasarım Stüdyosu** — stil, üç motif, palet ve seed seçip tasarım üretin.
3. Üretim sonucunda simetri, seam, tekrar ve palet kapsamını gösterin.
4. Aynı seed ile tekrar çalıştırıp SHA-256 değerinin aynı olduğunu gösterin.
5. PNG, JSON ve bağımsız HTML raporlarını indirin.
6. **Varyant Laboratuvarı** — dört seed varyantını yan yana üretin.
7. **Koleksiyon Arama** — son tasarımlardan birini sorgulayın.
   Sonuçlarda 235 kısıtlı katalog referansı ile üretilen tasarımlar birlikte sıralanır; katalog
   kayıtları "eğitim için kullanılamaz" etiketiyle gösterilir.
8. **Model & LoRA Kayıt Defteri** — izinli özel veri bağlanmadan açılmayan yönetişim kapılarını anlatın.

## 4. Söylenmesi gereken kanıt sınırları

- CPU prosedürel motoru `DEMO_ONLY` durumundadır; SDXL kalite iddiası taşımaz.
- Dijital analiz üretilebilirlik onayı değildir.
- Benzerlik araması hukuki özgünlük veya telif güvenliği sonucu değildir.
- Şirket verisi ancak lisans/provenance manifesti onayından sonra LoRA eğitimine alınmalıdır.
- Katalog snapshot'ı `RESTRICTED_REFERENCE_ONLY` durumundadır ve eğitim hattına bağlanmamıştır.

## 5. Üretilen artifact'lar

- Görseller: `artifacts/generations/`
- JSON ve HTML raporları: `artifacts/reports/`
- SQLite: `artifacts/carpet_designer.db`
