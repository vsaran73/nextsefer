!macro customInstall
  ; Kısayol dosyasını oluştur
  CreateShortCut "$DESKTOP\NextSefer.lnk" "$INSTDIR\NextSefer.bat" "" "$INSTDIR\resources\app.asar.unpacked\icon.ico"
  
  ; Başlat Menüsüne kısayol ekle
  CreateShortCut "$SMPROGRAMS\NextSefer\NextSefer.lnk" "$INSTDIR\NextSefer.bat" "" "$INSTDIR\resources\app.asar.unpacked\icon.ico"
  
  ; AutoStart için kayıt defteri anahtarı ekle (İsteğe bağlı)
  ; WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "NextSefer" '"$INSTDIR\NextSefer.bat"'

  ; Visual C++ 2015-2022 Redistributable'ı kur
  ExecWait '"$SYSDIR\msiexec.exe" /i "https://aka.ms/vs/17/release/vc_redist.x64.exe" /passive /norestart'
!macroend 