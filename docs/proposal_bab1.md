# BAB 1: PENDAHULUAN

## 1.1 Latar Belakang

Indonesia merupakan salah satu negara dengan tingkat kerawanan bencana
tertinggi di dunia. Berdasarkan data Badan Nasional Penanggulangan
Bencana (BNPB), Indonesia mencatat lebih dari 3.500 kejadian bencana
setiap tahunnya yang berdampak pada jutaan jiwa masyarakat. Posisi
geografis Indonesia yang berada di Cincin Api Pasifik (*Ring of Fire*)
menjadikan negara ini rentan terhadap berbagai bencana alam, mulai dari
gempa bumi, tsunami, letusan gunung berapi, banjir, hingga tanah
longsor.

Dalam situasi pascabencana, operasi pencarian dan pertolongan (*Search
and Rescue*/SAR) merupakan fase kritis yang menentukan keselamatan
korban. Setiap menit yang terbuang dalam proses pencarian berpotensi
merenggut nyawa. Namun, tim SAR seringkali menghadapi hambatan
signifikan: kondisi medan yang berbahaya, keterbatasan jangkauan visual
di area terdampak yang luas, serta risiko keselamatan personel yang
tinggi apabila masuk ke zona berbahaya tanpa informasi yang memadai.

Penggunaan *drone* dalam survei udara pascabencana telah menjadi solusi
yang semakin populer dalam beberapa tahun terakhir. *Drone* memungkinkan
tim SAR untuk memperoleh gambaran udara area terdampak secara cepat
tanpa harus menempatkan personel dalam bahaya. Namun, analisis citra
yang dihasilkan *drone* masih dilakukan secara manual oleh operator,
sebuah proses yang lambat, melelahkan, dan rentan terhadap kesalahan
manusia (*human error*). Operator yang kelelahan setelah jam-jam
pertama pascabencana berpotensi melewatkan keberadaan korban yang
tersembunyi atau berada dalam kondisi tidak bergerak.

Selain itu, solusi analisis citra berbasis kecerdasan buatan yang ada
saat ini umumnya bergantung pada *cloud computing* — mengirimkan data
citra ke server eksternal untuk diproses. Pendekatan ini memiliki dua
kelemahan fatal dalam konteks bencana: pertama, jaringan internet di
wilayah terdampak bencana seringkali lumpuh; kedua, pengiriman data
citra lokasi korban ke server pihak ketiga menimbulkan permasalahan
kedaulatan data yang krusial dalam operasi SAR pemerintah.

Hingga saat ini, belum tersedia sistem deteksi korban berbasis
kecerdasan buatan yang memenuhi tiga syarat sekaligus: (1) ringan dan
efisien secara komputasi sehingga dapat berjalan pada perangkat standar
tanpa infrastruktur khusus, (2) mampu beroperasi sepenuhnya secara
luring (*offline*) tanpa ketergantungan jaringan, dan (3) mampu
menghasilkan informasi lokasi korban yang dapat langsung ditindaklanjuti
oleh tim SAR di lapangan.

Kesenjangan inilah yang menjadi landasan pengembangan RescueVision Edge
— sebuah sistem visi komputer berbasis kecerdasan buatan yang dirancang
khusus untuk memenuhi ketiga syarat tersebut dalam satu paket solusi
yang komprehensif dan berdaulat secara teknologi.

---

## 1.2 Rumusan Masalah

Berdasarkan latar belakang yang telah diuraikan, rumusan masalah dalam
penelitian ini adalah sebagai berikut:

1. Bagaimana membangun sistem deteksi korban dari citra *drone* yang
   mampu berjalan sepenuhnya secara luring (*offline*) tanpa
   ketergantungan pada *cloud computing* maupun infrastruktur jaringan
   eksternal?

2. Bagaimana merancang arsitektur model *computer vision* yang memenuhi
   batasan sumber daya komputasi ketat — ukuran model maksimal 50 MB
   dan waktu inferensi maksimal 3 detik per citra pada CPU standar —
   tanpa mengorbankan akurasi deteksi yang memadai untuk operasi SAR?

3. Bagaimana menghasilkan keluaran sistem yang dapat langsung
   ditindaklanjuti oleh koordinator SAR, berupa koordinat geografis
   estimasi posisi korban yang diturunkan dari metadata GPS citra
   *drone*?

---

## 1.3 Tujuan

Tujuan pengembangan sistem RescueVision Edge adalah:

1. Membangun sistem deteksi korban pascabencana dari citra udara *drone*
   yang berjalan sepenuhnya secara luring, tanpa dependensi pada API
   atau layanan *cloud* eksternal apapun.

2. Mengembangkan model *object detection* berbasis YOLOv8n yang
   memenuhi seluruh batasan teknis (*constraint*) Track A: *The Edge
   Vision* — ukuran ≤50 MB, latensi ≤3 detik di CPU, dan
   kompatibilitas penuh dengan lingkungan *CPU-only*.

3. Menghasilkan keluaran sistem berupa *bounding box* deteksi korban
   beserta koordinat GPS estimasi posisi yang dapat langsung digunakan
   oleh tim SAR untuk menentukan prioritas zona pencarian.

4. Membuktikan bahwa sistem *AI* yang ringan, adaptif, dan berdaulat
   secara teknologi dapat dikembangkan untuk memperkuat ketahanan
   nasional dalam menghadapi situasi bencana, sejalan dengan tema
   *"Digital Sovereignty: Empowering National Resilience with Adaptive
   Intelligence"*.

---

## 1.4 Manfaat

**Bagi Tim SAR dan BASARNAS:**
Sistem ini memungkinkan analisis citra *drone* yang sebelumnya
membutuhkan 10–30 menit per foto secara manual menjadi selesai dalam
kurang dari 1 detik, serta memberikan koordinat estimasi lokasi korban
yang dapat langsung dimasukkan ke perangkat GPS lapangan.

**Bagi Kedaulatan Data Nasional:**
Seluruh pemrosesan dilakukan secara lokal — tidak ada data citra atau
koordinat korban yang dikirimkan ke server pihak ketiga, menjaga
kerahasiaan operasi SAR dan privasi korban sesuai dengan amanat
Undang-Undang Perlindungan Data Pribadi (UU PDP No. 27 Tahun 2022).

**Bagi Pengembangan Teknologi AI Nasional:**
Penelitian ini mendemonstrasikan bahwa mahasiswa Indonesia mampu
mengembangkan sistem *AI* kelas dunia yang adaptif terhadap batasan
teknis ekstrem, dengan memanfaatkan ekosistem *open source* global
secara berdaulat dan mandiri.
