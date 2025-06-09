<?php
/**
 * NextSefer Güncelleme Sunucusu Örneği
 * 
 * Bu basit PHP scripti, güncelleme kontrolü ve indirme işlemlerini yönetir.
 * Gerçek bir güncelleme sunucusu için bunu bir web sunucusuna yüklemeniz gerekir.
 */

// CORS ayarları
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");
header("Access-Control-Allow-Methods: GET, POST");
header("Access-Control-Max-Age: 3600");

// Sürüm bilgileri
$versions = [
    "1.0.0" => [
        "release_date" => "2025-06-01",
        "file" => "NextSefer_Setup_1.0.0.exe",
        "size" => 15000000, // bytes
        "release_notes" => "İlk sürüm",
        "is_critical" => false
    ],
    "1.0.1" => [
        "release_date" => "2025-06-07",
        "file" => "NextSefer_Setup_1.0.1.exe",
        "size" => 15100000, // bytes
        "release_notes" => "Tkinter hataları düzeltildi, arayüz iyileştirmeleri yapıldı.",
        "is_critical" => true
    ],
    "1.1.0" => [
        "release_date" => "2025-06-15",
        "file" => "NextSefer_Setup_1.1.0.exe",
        "size" => 15500000, // bytes
        "release_notes" => "Yeni özellikler eklendi: Gelişmiş raporlama, çoklu firma desteği.",
        "is_critical" => false
    ]
];

// En son sürüm
$latest_version = "1.1.0";

// URL dizinindeki isteğin ne olduğunu belirle
$request_uri = $_SERVER['REQUEST_URI'];
$path = parse_url($request_uri, PHP_URL_PATH);
$segments = explode('/', trim($path, '/'));
$endpoint = end($segments);

// Güncelleme kontrolü
if ($endpoint === 'check') {
    $current_version = isset($_GET['version']) ? $_GET['version'] : '1.0.0';
    
    // Sürüm karşılaştırması (basit string karşılaştırması)
    if (version_compare($current_version, $latest_version, '<')) {
        // Güncelleme mevcut
        $response = [
            'update_available' => true,
            'version' => $latest_version,
            'download_url' => "https://" . $_SERVER['HTTP_HOST'] . "/download/{$latest_version}/",
            'release_notes' => $versions[$latest_version]['release_notes'],
            'is_critical' => $versions[$latest_version]['is_critical'],
            'file_size' => $versions[$latest_version]['size'],
            'release_date' => $versions[$latest_version]['release_date']
        ];
    } else {
        // Güncelleme yok
        $response = [
            'update_available' => false,
            'message' => "En son sürümü kullanıyorsunuz: {$current_version}",
            'error' => false
        ];
    }
    
    echo json_encode($response);
    exit;
}

// Güncelleme indirme
if ($endpoint === 'download' && isset($segments[count($segments)-2]) && $segments[count($segments)-2] === 'download') {
    $version = isset($segments[count($segments)-1]) ? $segments[count($segments)-1] : null;
    
    if (!$version || !isset($versions[$version])) {
        http_response_code(404);
        echo json_encode(['error' => 'Belirtilen sürüm bulunamadı']);
        exit;
    }
    
    $file_path = __DIR__ . '/files/' . $versions[$version]['file'];
    
    if (!file_exists($file_path)) {
        http_response_code(404);
        echo json_encode(['error' => 'Güncelleme dosyası bulunamadı']);
        exit;
    }
    
    // Dosya indirme işlemleri
    header('Content-Description: File Transfer');
    header('Content-Type: application/octet-stream');
    header('Content-Disposition: attachment; filename="' . basename($file_path) . '"');
    header('Expires: 0');
    header('Cache-Control: must-revalidate');
    header('Pragma: public');
    header('Content-Length: ' . filesize($file_path));
    flush(); // Çıktı tamponunu temizle
    readfile($file_path);
    exit;
}

// Tanımlanmamış endpoint için hata
http_response_code(400);
echo json_encode(['error' => 'Geçersiz istek']);
?> 
 
 
 