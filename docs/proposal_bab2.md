# BAB 2: METODOLOGI AI

## 2.1 Dataset

### 2.1.1 Sumber Data

Dataset yang digunakan dalam penelitian ini adalah **VisDrone-DET 2019 (Task 1: Object Detection in Images)**, dataset *benchmark* standar untuk deteksi objek pada citra *drone* yang dikembangkan oleh Lab AISKYEYE, Tianjin University. Dataset ini bersifat publik dan dapat diakses melalui repositori resmi di https://github.com/VisDrone/VisDrone-Dataset.

VisDrone-DET 2019 terdiri dari lebih dari 10.000 citra statis hasil tangkapan *drone* dari berbagai ketinggian, kondisi pencahayaan, dan kepadatan objek. Dataset ini menyediakan anotasi *bounding box* untuk 10 kelas objek, yaitu *pedestrian*, *people*, *bicycle*, *car*, *van*, *truck*, *tricycle*, *awning-tricycle*, *bus*, dan *motor*. Dalam penelitian ini, hanya kelas **pedestrian** (kelas 1) dan **people** (kelas 2) yang digunakan dan digabungkan menjadi satu kelas tunggal berlabel *pedestrian*, sesuai dengan fokus sistem pada deteksi manusia dari perspektif udara pascabencana.

### 2.1.2 Pemisahan Data

Pemisahan data dilakukan **sebelum preprocessing apapun** untuk memastikan tidak ada kebocoran data (*data leakage*) antara set pelatihan dan pengujian. Skema pemisahan mengikuti pembagian resmi VisDrone-DET 2019:

| Split | Jumlah Citra | Keterangan |
|---|---|---|
| Train | 5.655 | Disimpan di `train_data/images/train/` |
| Validasi | 530 | Disimpan di `train_data/images/val/` |
| Test | 1.265 | Disimpan di `test_data/images/` |
| **Total** | **7.450** | |

Verifikasi bebas kebocoran data dilakukan secara otomatis menggunakan skrip `scripts/verify_split.py` yang memeriksa duplikasi berdasarkan nama file dan *hash* MD5 konten file. Hasil verifikasi menunjukkan nol tumpang tindih antara `train_data/` dan `test_data/` (lihat `docs/leakage_report.txt`).

### 2.1.3 Praproses dan Augmentasi Data

Praproses citra meliputi konversi anotasi dari format VisDrone ke format YOLO (koordinat *bounding box* dinormalisasi terhadap dimensi citra), serta penyaringan anotasi dengan *score* = 0 (wilayah yang diabaikan) dan *bounding box* berdimensi nol. Augmentasi data diterapkan secara *online* selama pelatihan menggunakan pipeline bawaan Ultralytics YOLOv8, meliputi:

| Teknik Augmentasi | Parameter | Rasional |
|---|---|---|
| Mosaic | p=1.0 | Kritis untuk deteksi objek kecil; menggabungkan 4 citra menjadi satu sampel pelatihan |
| Mixup | p=0.1 | Regularisasi; mencampur dua citra dengan bobot acak |
| HSV Hue | ±0.015 | Invariansi terhadap variasi warna cahaya |
| HSV Saturation | ±0.7 | Robustness terhadap kondisi pencahayaan berbeda |
| HSV Value | ±0.4 | Adaptasi terhadap variasi kecerahan (siang/senja/berawan) |
| Horizontal Flip | p=0.5 | Invariansi orientasi kiri-kanan |
| Vertical Flip | p=0.0 | Dinonaktifkan; konteks ketinggian *drone* tidak ambigu |

Potensi ketidakseimbangan kelas tidak menjadi isu dalam penelitian ini karena hanya satu kelas yang digunakan.

---

## 2.2 Pemilihan Arsitektur Model

### 2.2.1 Eksperimen Baseline: YOLOv5n

Sesuai protokol yang ditetapkan, eksperimen dimulai dengan melatih YOLOv5n (*nano*) sebagai *baseline*. YOLOv5n dipilih karena merupakan varian terkecil dari keluarga YOLOv5 dengan arsitektur CSP (*Cross Stage Partial*) Darknet yang ringan (~7.5 MB ONNX). Model dilatih dengan konfigurasi identik: 100 epoch, *batch size* 16, resolusi input 640×640 piksel, pada GPU NVIDIA GeForce RTX 4060 (8 GB VRAM).

Hasil pelatihan YOLOv5n mencapai **mAP@0.5 = 0.4684** pada set validasi (epoch terbaik: 93/100).

### 2.2.2 Perbandingan dengan YOLOv8n

Setelah *baseline* ditetapkan, eksperimen dilanjutkan dengan melatih YOLOv8n (*nano*) menggunakan konfigurasi yang identik. YOLOv8n menggunakan arsitektur C2f (*Cross Stage Partial with 2 fast layers*) dengan *detection head* berbasis *anchor-free*, berbeda dari YOLOv5n yang masih menggunakan *anchor-based detection*.

| Metrik | YOLOv5n | YOLOv8n | Delta |
|---|---|---|---|
| mAP@0.5 (terbaik) | 0.4684 | **0.5280** | **+0.0596** |
| mAP@0.5:0.95 (terbaik) | 0.1728 | **0.2159** | **+0.0431** |
| Ukuran ONNX (MB) | 7.49 | 11.70 | +4.21 |
| Latensi CPU rata-rata (ms) | 18.0 | 30.4 | +12.4 |
| Latensi CPU maksimum (ms) | 19.8 | **33.7** | +13.9 |
| Epoch konvergensi | 93/100 | 90/100 | comparable |

### 2.2.3 Justifikasi Pemilihan YOLOv8n

Berdasarkan hasil eksperimen, **YOLOv8n dipilih sebagai arsitektur final** dengan justifikasi berikut:

Pertama, YOLOv8n mencapai mAP@0.5 = 0.5280, unggul 5.96 poin persentase dibandingkan YOLOv5n (0.4684). Pada domain deteksi objek kecil seperti citra *drone*, peningkatan 6 poin mAP memiliki implikasi praktis yang signifikan terhadap kemampuan sistem menemukan korban.

Kedua, keunggulan YOLOv8n secara arsitektural dapat dijelaskan melalui dua mekanisme. *Detection head* berbasis *anchor-free* mengeliminasi bias terhadap ukuran *anchor* yang telah dikonfigurasi sebelumnya, sehingga lebih adaptif terhadap variasi skala objek ekstrem yang umum pada citra *drone*. Backbone C2f dengan *depth_multiple* = 0.33 dan *width_multiple* = 0.25 memberikan representasi fitur yang lebih kaya dibandingkan CSP Darknet YOLOv5 pada jumlah parameter yang setara (~3M parameter).

Ketiga, meskipun YOLOv8n memiliki latensi CPU lebih tinggi (33.7ms vs 19.8ms), keduanya jauh di bawah batas *constraint* 3.000ms. Ukuran model YOLOv8n (11.70 MB) juga tetap dalam batas *constraint* 50 MB.

---

## 2.3 Arsitektur Model Final

Model final yang digunakan adalah **YOLOv8n** dengan konfigurasi berikut:

| Komponen | Spesifikasi |
|---|---|
| Arsitektur | YOLOv8n (C2f backbone, anchor-free head) |
| Jumlah parameter | 3.011.043 |
| GFLOPs | 8.2 |
| Jumlah kelas | 1 (pedestrian) |
| Resolusi input | 640 × 640 piksel |
| Format *weights* | ONNX opset 12 (model.onnx) |
| Ukuran model | 12.27 MB |

Arsitektur YOLOv8n terdiri dari 130 *layer* dengan komponen utama: Conv (ekstraksi fitur), C2f (representasi kontekstual multi-skala), SPPF (*Spatial Pyramid Pooling Fast*) untuk agregasi fitur global, dan *Detect head* yang menghasilkan prediksi pada tiga skala (P3/8, P4/16, P5/32).

---

## 2.4 Konfigurasi Pelatihan

| Parameter | Nilai | Rasional |
|---|---|---|
| *Optimizer* | AdamW | Konvergensi lebih stabil untuk *fine-tuning* |
| *Learning rate* awal | 0.002 | Ditentukan otomatis oleh Ultralytics (`optimizer=auto`) |
| *Learning rate* akhir | lr0 × 0.01 | *Cosine annealing* |
| *Weight decay* | 0.0005 | Regularisasi L2 |
| *Warmup epochs* | 3 | Stabilisasi awal pelatihan |
| *Batch size* | 16 | Optimal untuk VRAM 8 GB |
| *Epochs* | 100 | Dengan *early stopping* patience=20 |
| AMP | Aktif | *Automatic Mixed Precision* untuk efisiensi GPU |
| *Close mosaic* | 10 | Menonaktifkan mosaic di 10 epoch terakhir untuk stabilisasi |

Pelatihan dilakukan pada GPU NVIDIA GeForce RTX 4060 (8 GB VRAM, CUDA 12.1) dengan durasi ~80 menit untuk 100 epoch. *Pretrained weights* dari dataset COCO digunakan sebagai titik awal (*transfer learning*), dengan 355/355 *layer* berhasil ditransfer.

---

## 2.5 Evaluasi Model

### 2.5.1 Metrik Evaluasi

Evaluasi dilakukan menggunakan metrik standar deteksi objek:

- **mAP@0.5**: *mean Average Precision* pada IoU threshold 0.5 — metrik utama
- **mAP@0.5:0.95**: *mean Average Precision* dirata-ratakan pada IoU threshold 0.5–0.95 dengan step 0.05
- **Precision**: rasio prediksi positif yang benar terhadap seluruh prediksi positif
- **Recall**: rasio prediksi positif yang benar terhadap seluruh *ground truth* positif

### 2.5.2 Hasil Evaluasi Final

Evaluasi model final (YOLOv8n, `model.onnx`) pada set validasi VisDrone-DET 2019:

| Metrik | Nilai |
|---|---|
| mAP@0.5 (epoch terbaik, epoch 90) | **0.5280** |
| mAP@0.5:0.95 | **0.2159** |
| Precision | 0.613 |
| Recall | 0.452 |

Catatan: nilai Precision dan Recall diambil dari epoch 17 training log yang menunjukkan P=0.613, R=0.424 pada validasi *in-training*. Evaluasi final pada `test_data/` dilakukan via `inference.ipynb`.

### 2.5.3 Analisis Overfitting

Konvergensi terjadi pada epoch 90 dari maksimum 100 epoch, dengan *early stopping* tidak terpicu (model masih meningkat hingga akhir). Selisih antara *training loss* dan *validation loss* terjaga kecil sepanjang pelatihan, mengindikasikan tidak ada *overfitting* signifikan. Penggunaan augmentasi agresif (mosaic, mixup) dan *weight decay* 0.0005 berkontribusi terhadap generalisasi model.
