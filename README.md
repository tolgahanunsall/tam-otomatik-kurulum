# Note Backup Tool

**Notion ve Obsidian icin Otomatik Yedekleme Araci**

Obsidian vault'larinizi ve Notion sayfalarinizi otomatik olarak GitHub ve/veya Dropbox'a yedekleyin. Mac, Windows ve Linux'ta calisir.

---

## Ozellikler

- **Obsidian Vault Yedekleme** - Tum Markdown dosyalari, ekler ve ayarlar
- **Notion Yedekleme** - API uzerinden sayfalar ve veritabanlari (Markdown/HTML)
- **GitHub Hedefi** - Otomatik commit ve push ile Git repository yedekleme
- **Dropbox Hedefi** - Dropbox API ile bulut yedekleme (buyuk dosya destegi)
- **Capraz Platform** - macOS, Windows ve Linux destegi
- **Otomatik Zamanlama** - cron (Linux), launchd (macOS), Task Scheduler (Windows)
- **Esnek Yapilandirma** - YAML tabanli kolay konfigrasyon
- **Akilli Haric Tutma** - Gereksiz dosyalari (cache, workspace vb.) otomatik atla

---

## Hizli Baslangic

### Gereksinimler

- Python 3.8 veya ustu
- pip (Python paket yoneticisi)
- Git (GitHub yedeklemesi icin)

### 1. Kurulum

#### Linux / macOS

```bash
# Repoyu klonlayin
git clone https://github.com/YOUR_USERNAME/note-backup-tool.git
cd note-backup-tool

# Kurulum scriptini calistirin
chmod +x scripts/install.sh
./scripts/install.sh
```

#### Windows

```powershell
# Repoyu klonlayin
git clone https://github.com/YOUR_USERNAME/note-backup-tool.git
cd note-backup-tool

# Kurulum scriptini calistirin
scripts\install.bat
```

#### Manuel Kurulum (Tum Platformlar)

```bash
# Repoyu klonlayin
git clone https://github.com/YOUR_USERNAME/note-backup-tool.git
cd note-backup-tool

# Sanal ortam olusturun
python3 -m venv venv

# Sanal ortami aktive edin
# Linux/macOS:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# Bagimliliklari yukleyin
pip install -r requirements.txt

# Yapilandirma dosyasini olusturun
cp config.example.yaml config.yaml
```

### 2. Yapilandirma

`config.yaml` dosyasini duzenleyin:

```bash
# Linux/macOS
nano config.yaml
# veya
vim config.yaml

# Windows
notepad config.yaml
```

#### Temel Yapilandirma Ornegi

```yaml
general:
  backup_dir: "~/note-backups"
  log_level: "INFO"
  log_file: "~/note-backups/logs/backup.log"

sources:
  obsidian:
    enabled: true
    vaults:
      - name: "BenimVault"
        path: "~/Documents/ObsidianVaults/BenimVault"
    exclude_patterns:
      - ".obsidian/workspace.json"
      - ".trash/"

  notion:
    enabled: false
    api_token: "YOUR_NOTION_TOKEN"
    export_format: "markdown"

targets:
  github:
    enabled: true
    token: "YOUR_GITHUB_TOKEN"
    repository: "kullanici/obsidian-backup"
    branch: "main"
    commit_message: "Otomatik yedekleme: {date}"

  dropbox:
    enabled: false
    access_token: "YOUR_DROPBOX_TOKEN"
    remote_path: "/NoteBackups"

schedule:
  time: "03:00"
  frequency: "daily"
```

### 3. API Token'lari Alma

#### GitHub Personal Access Token

1. [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens) adresine gidin
2. "Generate new token (classic)" tiklayin
3. Token'a bir isim verin (orn. "note-backup")
4. Su izinleri secin:
   - `repo` (tam repository erisimi)
5. Token'i olusturun ve `config.yaml` dosyasina yapisitirin
6. **Hedef repository'yi** GitHub'da olusturmayi unutmayin!

#### Notion Integration Token

1. [Notion Integrations](https://www.notion.so/my-integrations) sayfasina gidin
2. "New integration" tiklayin
3. Bir isim verin ve workspace'inizi secin
4. "Internal Integration Token" degerini kopyalayin
5. `config.yaml` dosyasina yapisitirin
6. **Onemli:** Yedeklemek istediginiz sayfalarda entegrasyonu paylasmaniz gerekir:
   - Sayfaya gidin > Sag ust kosedeki `...` > `Connections` > Entegrasyonunuzu ekleyin

#### Dropbox Access Token

1. [Dropbox App Console](https://www.dropbox.com/developers/apps) adresine gidin
2. "Create app" tiklayin
3. "Scoped access" ve "Full Dropbox" secin
4. Uygulamayi olusturun
5. "Permissions" sekmesinde `files.content.write` ve `files.content.read` izinlerini verin
6. "Settings" sekmesinde "Generate access token" tiklayin
7. Token'i `config.yaml` dosyasina yapisitirin

**Uzun Sureli Erisim (Onerilen):**
Kisa sureli token yerine refresh token kullanmak icin:
```yaml
dropbox:
  enabled: true
  refresh_token: "YOUR_REFRESH_TOKEN"
  app_key: "YOUR_APP_KEY"
  app_secret: "YOUR_APP_SECRET"
  remote_path: "/NoteBackups"
```

### 4. Yedeklemeyi Calistirma

```bash
# Sanal ortami aktive edin (yapmadiysaniz)
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Yedeklemeyi baslatin
python backup.py

# Ayrintili log ile
python backup.py --verbose

# Ozel config dosyasi ile
python backup.py --config /path/to/config.yaml
```

### 5. Otomatik Zamanlama

Gunluk otomatik yedekleme icin:

```bash
# Zamanlamayi kur
python backup.py schedule install

# Zamanlama durumunu kontrol et
python backup.py schedule status

# Zamanlamayi kaldir
python backup.py schedule remove
```

Bu komut platformunuza gore otomatik olarak dogru zamanlama yontemini kullanir:

| Platform | Yontem | Detay |
|----------|--------|-------|
| **Linux** | cron | `crontab -l` ile kontrol edin |
| **macOS** | launchd | `~/Library/LaunchAgents/` altinda plist |
| **Windows** | Task Scheduler | `schtasks /Query /TN NoteBackupTool` |

---

## Gelismis Kullanim

### Birden Fazla Vault

```yaml
sources:
  obsidian:
    enabled: true
    vaults:
      - name: "Kisisel"
        path: "~/Documents/Vaults/Kisisel"
      - name: "Is"
        path: "~/Documents/Vaults/Is"
      - name: "Projeler"
        path: "D:/ObsidianVaults/Projeler"  # Windows
```

### Hem GitHub Hem Dropbox

```yaml
targets:
  github:
    enabled: true
    token: "ghp_xxxxx"
    repository: "kullanici/notes-backup"
    branch: "main"

  dropbox:
    enabled: true
    access_token: "sl.xxxxx"
    remote_path: "/NoteBackups"
```

### Haftalik Yedekleme

```yaml
schedule:
  time: "02:00"
  frequency: "weekly"
  weekly_day: 6  # Pazar gunu (0=Pazartesi, 6=Pazar)
```

### Saatlik Yedekleme

```yaml
schedule:
  time: "00:30"       # Her saatin 30. dakikasinda
  frequency: "hourly"
```

---

## Proje Yapisi

```
note-backup-tool/
├── backup.py                      # Ana giris noktasi
├── config.example.yaml            # Ornek yapilandirma
├── config.yaml                    # Sizin yapilandirmaniz (gitignore'da)
├── requirements.txt               # Python bagimliliklari
├── setup.py                       # Paket kurulumu
├── LICENSE                        # MIT Lisansi
├── README.md                      # Bu dosya
├── src/
│   ├── __init__.py
│   ├── config.py                  # Yapilandirma yukleyici
│   ├── logger.py                  # Log sistemi
│   ├── sources/
│   │   ├── obsidian.py            # Obsidian vault yedekleme
│   │   └── notion.py              # Notion API yedekleme
│   ├── targets/
│   │   ├── github_target.py       # GitHub repository yedekleme
│   │   └── dropbox_target.py      # Dropbox bulut yedekleme
│   └── scheduler/
│       ├── cron_setup.py          # Linux cron zamanlama
│       ├── launchd_setup.py       # macOS launchd zamanlama
│       └── taskscheduler_setup.py # Windows Task Scheduler
└── scripts/
    ├── install.sh                 # Linux/macOS kurulum scripti
    └── install.bat                # Windows kurulum scripti
```

---

## Sorun Giderme

### "Config file not found" hatasi
```bash
# config.yaml dosyasini olusturdunuz mu?
cp config.example.yaml config.yaml
# Sonra duzenleyin
```

### "Obsidian vault not found" uyarisi
- Vault yolunun dogru oldugunu kontrol edin
- `~` yerine tam yol da kullanabilirsiniz: `/home/kullanici/Documents/Vault`
- Windows'ta: `C:/Users/kullanici/Documents/Vault` (ters slash yerine duz slash)

### GitHub push basarisiz
- Token'in `repo` iznine sahip oldugundan emin olun
- Hedef repository'nin GitHub'da olusturulmus oldugundan emin olun
- Repository adinin `kullanici/repo` formatinda oldugundan emin olun

### Notion API hatasi
- Integration token'inin gecerli oldugunu kontrol edin
- Yedeklemek istediginiz sayfalarda entegrasyonun **paylasildığından** emin olun
- Rate limit'e takildiysaniz, script otomatik olarak bekleyecektir

### Dropbox authentication hatasi
- Access token'inin suresi dolmus olabilir
- Uzun sureli erisim icin refresh token kullanin
- App Console'da gerekli izinlerin verildiginden emin olun

---

## Lisans

MIT License - Detaylar icin [LICENSE](LICENSE) dosyasina bakin.
