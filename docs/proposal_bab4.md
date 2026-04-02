# BAB 4: RANCANGAN SISTEM & BISNIS

## 4.1 Arsitektur Sistem

### 4.1.1 Gambaran Umum

RescueVision Edge dibangun sebagai sistem berbasis web yang berjalan
sepenuhnya secara lokal (*localhost*) pada laptop koordinator lapangan.
Sistem tidak memerlukan koneksi internet dalam operasionalnya, sesuai
dengan skenario nyata di wilayah bencana yang seringkali mengalami
gangguan infrastruktur jaringan.

Arsitektur sistem terdiri dari tiga komponen utama yang terhubung
secara modular:

```
[Input Layer]          [Processing Layer]      [Output Layer]
Foto DJI Drone    →    FastAPI Backend     →   Web Dashboard
(JPEG + GPS EXIF)      YOLOv8n ONNX           Bounding Box
                       EXIF Parser            Koordinat GPS
                       Coordinate Mapper      Tabel Korban
                                              Export CSV/JSON
```

### 4.1.2 Alur Operasional

Alur penggunaan sistem dalam skenario operasi SAR pascabencana:

**Fase 1 — Pengumpulan Data Udara:**
Operator drone menerbangkan wahana DJI di atas area terdampak dan
merekam citra udara. Drone DJI secara otomatis menyimpan koordinat
GPS, ketinggian terbang, dan sudut *gimbal* dalam metadata EXIF setiap
foto yang dihasilkan.

**Fase 2 — Transfer & Analisis:**
Setelah mendarat, operator mentransfer foto dari kartu memori (*SD
card*) ke laptop koordinator. Foto kemudian diunggah ke antarmuka web
RescueVision Edge yang berjalan di *localhost*. Sistem memproses setiap
foto secara otomatis: membaca metadata EXIF, menjalankan inferensi
model YOLOv8n, dan menghitung koordinat geografis setiap korban yang
terdeteksi.

**Fase 3 — Tindak Lanjut SAR:**
Koordinator SAR membaca hasil deteksi berupa peta visual dengan
*bounding box* dan tabel koordinat GPS per korban. Informasi ini
diteruskan ke tim SAR di lapangan melalui radio atau perangkat GPS
untuk menentukan prioritas zona pencarian.

### 4.1.3 Kalkulasi Koordinat Korban

Setiap foto DJI menyimpan metadata EXIF yang mencakup:
- `GPSLatitude` dan `GPSLongitude` — posisi drone saat foto diambil
- `RelativeAltitude` — ketinggian terbang relatif terhadap permukaan
- `GimbalYawDegree` — arah hadap kamera

Dari metadata ini, sistem menghitung koordinat geografis setiap korban
menggunakan transformasi proyeksi perspektif:

```
# Estimasi ground sampling distance (GSD)
GSD = (sensor_width × altitude) / (focal_length × image_width)

# Offset piksel dari pusat foto ke pusat bounding box
dx_px = cx_box - (image_width / 2)
dy_px = cy_box - (image_height / 2)

# Konversi ke meter
dx_m = dx_px × GSD
dy_m = dy_px × GSD

# Konversi ke koordinat geografis
lat_korban = lat_drone + (dy_m / 111320)
lon_korban = lon_drone + (dx_m / (111320 × cos(lat_drone)))
```

Output koordinat memiliki akurasi estimasi ±5–15 meter pada ketinggian
terbang 50–100 meter, cukup untuk menentukan zona pencarian SAR.

---

## 4.2 Rancangan Teknologi (Tech Stack)

| Komponen | Teknologi | Alasan Pemilihan |
|---|---|---|
| Backend API | FastAPI (Python) | Ringan, async, mudah diintegrasikan |
| AI Inference | ONNX Runtime | CPU-only, offline, <32ms per foto |
| EXIF Parser | `piexif` / `Pillow` | Akses GPS metadata foto DJI |
| Frontend | HTML + JavaScript (Vanilla) | Tanpa framework berat, mudah dimodifikasi |
| Visualisasi | Canvas API / OpenCV.js | Render bounding box di browser |
| Data Export | CSV + JSON | Kompatibel dengan GPS tools & GIS |
| Komunikasi | REST API (localhost) | Modular, siap Dynamic Injection |

Seluruh *stack* berjalan di *localhost* tanpa dependensi cloud. Tidak
ada data foto atau koordinat yang dikirim ke server eksternal.

### 4.2.1 Desain API (Endpoint Utama)

```
POST /detect
  Input : multipart/form-data (file gambar)
  Output: {
    "detections": [
      {
        "id": 1,
        "confidence": 0.87,
        "bbox": [x1, y1, x2, y2],
        "lat": -7.3421,
        "lon": 110.4523,
        "zone": "A-3"
      }
    ],
    "total_victims": 3,
    "inference_ms": 31.2,
    "image_gps": {"lat": -7.3418, "lon": 110.4521}
  }

POST /detect/batch
  Input : folder path atau multiple files
  Output: agregasi deteksi dari semua foto

GET /export/csv
  Output: file CSV koordinat semua korban terdeteksi

GET /health
  Output: status sistem, versi model, provider inferensi
```

Desain API yang modular memungkinkan sistem menerima *Dynamic
Injection* dari panitia pada Tahap 3 tanpa mengubah komponen inti.

---

## 4.3 Antarmuka Pengguna (UI/UX)

Antarmuka dirancang untuk dua peran pengguna dengan kebutuhan berbeda:

**Operator Drone** — fokus pada kecepatan upload dan konfirmasi deteksi:
- *Drag & drop* upload foto atau folder
- *Progress bar* pemrosesan per foto
- *Preview* foto dengan *bounding box* overlay

**Koordinator SAR** — fokus pada informasi lokasi dan prioritas:
- Tabel korban terdeteksi dengan koordinat GPS
- Peta mini (menggunakan Leaflet.js offline tiles)
- Tombol *export* koordinat ke CSV untuk dimasukkan ke GPS handheld
- Ringkasan: total korban, zona dengan densitas tertinggi

---

## 4.4 Rancangan Integrasi Tahap 3

Sesuai mekanisme *Dynamic Injection* Tahap 3, sistem dirancang dengan
arsitektur modular yang dapat menerima variabel atau logika tambahan
tanpa *crash*. Komponen yang dirancang untuk fleksibilitas:

**Config Layer** — seluruh parameter sistem (confidence threshold,
input resolution, zona grid, format export) disimpan dalam file
`config.json` yang dapat dimodifikasi tanpa mengubah kode:

```json
{
  "conf_threshold": 0.25,
  "iou_threshold": 0.45,
  "input_size": 640,
  "grid_zone_size_m": 50,
  "export_format": ["csv", "json"],
  "max_batch_size": 100
}
```

**Plugin Endpoint** — endpoint `/inject` dirancang khusus untuk
menerima *Runtime Variable* dari panitia:

```
POST /inject
  Input : {"variable": "conf_threshold", "value": 0.4}
  Output: {"status": "updated", "applied": true}
```

Dengan arsitektur ini, panitia dapat menginjeksi perubahan parameter
apapun saat *countdown* dimulai tanpa menyebabkan *crash* pada sistem.

---

## 4.5 Analisis Dampak & Keberlanjutan

### 4.5.1 Dampak Sosial

RescueVision Edge secara langsung mengatasi tiga hambatan utama dalam
operasi SAR pascabencana Indonesia:

**Kecepatan Respons:** Analisis citra manual oleh operator membutuhkan
waktu 10–30 menit per foto untuk mengidentifikasi korban. Dengan
RescueVision Edge, analisis dilakukan dalam <1 detik per foto,
memungkinkan pemrosesan ratusan foto dalam hitungan menit.

**Kedaulatan Data:** Sistem berjalan sepenuhnya *offline* — tidak ada
data citra atau koordinat korban yang dikirim ke server eksternal.
Ini krusial dalam konteks operasi SAR pemerintah yang memiliki
sensitivitas data lokasi korban.

**Aksesibilitas:** Model berjalan di laptop standar tanpa GPU khusus
(telah diverifikasi <32ms di CPU Intel i5 Gen 8+). Tidak diperlukan
infrastruktur komputasi mahal untuk mengoperasikan sistem.

### 4.5.2 Target Pengguna

| Segmen | Deskripsi | Estimasi Pengguna |
|---|---|---|
| BASARNAS | Badan SAR Nasional Indonesia | 4.800 personel |
| BPBD Provinsi | Badan Penanggulangan Bencana Daerah | 34 provinsi |
| TNI/Polri SAR Unit | Unit khusus SAR militer dan kepolisian | ~2.000 personel |
| NGO Kemanusiaan | Organisasi kemanusiaan bencana | 50+ organisasi |

### 4.5.3 Analisis Kompetitor

| Solusi | Kelemahan vs RescueVision Edge |
|---|---|
| Google Vision API | Membutuhkan internet, data dikirim ke cloud |
| AWS Rekognition | Biaya per-request, tidak tersedia di area bencana |
| Analisis manual | 10–30 menit/foto, rentan human error, fatigue |
| Sistem drone komersial | Harga >$50.000, terikat vendor spesifik |

RescueVision Edge adalah satu-satunya solusi yang menggabungkan
akurasi AI (mAP@0.5 = 0.528), kecepatan inferensi (<32ms CPU),
dan kedaulatan data penuh dalam satu paket yang dapat berjalan
di laptop koordinator lapangan tanpa koneksi internet.

### 4.5.4 Rencana Keberlanjutan

**Jangka Pendek (0–6 bulan):**
Pengujian lapangan bersama unit SAR lokal, penyempurnaan kalkulasi
koordinat GPS berdasarkan data lapangan nyata, dan penambahan
dukungan format video (analisis *frame-by-frame*).

**Jangka Menengah (6–18 bulan):**
Integrasi dengan sistem *Ground Control Station* DJI, penambahan
kelas deteksi (kendaraan terdampak, struktur runtuh), dan pengembangan
versi mobile untuk koordinator lapangan.

**Jangka Panjang (18+ bulan):**
Kolaborasi dengan BASARNAS dan BPBD untuk deployment nasional,
penelitian peningkatan akurasi dengan data bencana Indonesia spesifik,
dan potensi integrasi dengan sistem peringatan dini BMKG.

---

## 4.6 Etika Data & Privasi

Seluruh data citra dan koordinat korban diproses secara lokal dan
tidak pernah meninggalkan perangkat operator. Sistem tidak menyimpan
log inferensi secara permanen — data sesi dihapus otomatis saat
aplikasi ditutup. Koordinat korban yang diekspor dalam format CSV
hanya dapat diakses oleh koordinator yang menjalankan sistem,
sesuai dengan prinsip *need-to-know* dalam operasi SAR.

Model YOLOv8n dilatih menggunakan dataset publik VisDrone-DET 2019
yang tidak mengandung data identitas personal. Output sistem berupa
koordinat lokasi, bukan identitas individu, sehingga tidak melanggar
regulasi perlindungan data pribadi (UU PDP No. 27 Tahun 2022).
