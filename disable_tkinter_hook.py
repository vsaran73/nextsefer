"""
PyInstaller hook to disable Tkinter
This will prevent PyInstaller from including Tkinter and Tcl/Tk dependencies
"""

def hook(hook_api):
    # Tkinter modüllerini ve bağımlılıklarını dışla
    hook_api.add_runtime_module('_tkinter')
    hook_api.add_runtime_module('tkinter')
    hook_api.add_runtime_module('tkinter.ttk')
    hook_api.add_runtime_module('tkinter.filedialog')
    hook_api.add_runtime_module('tkinter.messagebox')
    hook_api.add_runtime_module('tkinter.constants')
    hook_api.add_runtime_module('tcl')
    hook_api.add_runtime_module('tk')
    
    # Bilgi mesajı
    print("Tkinter ve Tcl/Tk bağımlılıkları dışlandı.") 
 
 
 