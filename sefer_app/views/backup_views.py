from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from django.core.management import call_command
import os
import tempfile
import datetime
import json
import subprocess
from pathlib import Path
import traceback

def backup_view(request):
    """View for database backup and restore operations"""
    
    backup_folder = os.path.join(os.path.expanduser("~"), "NextSefer_Logs", "backups")
    # Ensure backup directory exists
    os.makedirs(backup_folder, exist_ok=True)
    
    # Get list of existing backups
    backup_files = []
    for file in os.listdir(backup_folder):
        if file.endswith('.json'):
            file_path = os.path.join(backup_folder, file)
            file_stats = os.stat(file_path)
            backup_files.append({
                'filename': file,
                'size': file_stats.st_size / 1000,  # KB
                'date': datetime.datetime.fromtimestamp(file_stats.st_mtime).strftime('%d.%m.%Y %H:%M:%S')
            })
    
    # Sort backups by date (newest first)
    backup_files = sorted(backup_files, key=lambda x: x['filename'], reverse=True)
    
    if request.method == 'POST':
        if 'create_backup' in request.POST:
            try:
                # Generate timestamp for filename
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                filename = f"nextsefer_backup_{timestamp}.json"
                filepath = os.path.join(backup_folder, filename)
                
                # Call Django's dumpdata command
                with open(filepath, 'w', encoding='utf-8') as f:
                    call_command('dumpdata', 
                                 exclude=['contenttypes', 'auth.permission', 'admin.logentry'],
                                 indent=2, 
                                 stdout=f)
                
                messages.success(request, f"Yedekleme başarıyla tamamlandı: {filename}")
                return redirect('backup')
            except Exception as e:
                traceback.print_exc()
                messages.error(request, f"Yedekleme sırasında hata: {str(e)}")
        
        elif 'download_backup' in request.POST:
            filename = request.POST.get('filename')
            if filename:
                filepath = os.path.join(backup_folder, filename)
                if os.path.exists(filepath):
                    response = FileResponse(open(filepath, 'rb'))
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response
                else:
                    messages.error(request, "Belirtilen yedek dosyası bulunamadı.")
        
        elif 'restore_backup' in request.POST:
            filename = request.POST.get('filename')
            if filename:
                filepath = os.path.join(backup_folder, filename)
                if os.path.exists(filepath):
                    try:
                        # First load the file to verify it's valid JSON
                        with open(filepath, 'r', encoding='utf-8') as f:
                            json.load(f)
                        
                        # Call Django's loaddata command
                        call_command('loaddata', filepath)
                        
                        messages.success(request, f"Yedek başarıyla geri yüklendi: {filename}")
                    except Exception as e:
                        traceback.print_exc()
                        messages.error(request, f"Yedek geri yükleme sırasında hata: {str(e)}")
                else:
                    messages.error(request, "Belirtilen yedek dosyası bulunamadı.")
        
        elif 'delete_backup' in request.POST:
            filename = request.POST.get('filename')
            if filename:
                filepath = os.path.join(backup_folder, filename)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        messages.success(request, f"Yedek dosyası silindi: {filename}")
                    except Exception as e:
                        messages.error(request, f"Dosya silinirken hata oluştu: {str(e)}")
                else:
                    messages.error(request, "Belirtilen yedek dosyası bulunamadı.")
        
        elif 'upload_backup' in request.POST and 'backup_file' in request.FILES:
            uploaded_file = request.FILES['backup_file']
            if uploaded_file.name.endswith('.json'):
                # Save the uploaded file
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                filename = f"uploaded_backup_{timestamp}.json"
                filepath = os.path.join(backup_folder, filename)
                
                with open(filepath, 'wb') as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)
                
                messages.success(request, f"Yedek dosyası yüklendi: {filename}")
            else:
                messages.error(request, "Yalnızca .json uzantılı dosyalar kabul edilir.")
    
    context = {
        'backup_files': backup_files,
        'today': timezone.now().date(),
    }
    return render(request, 'sefer_app/backup.html', context) 