"""
Bu modül, PyInstaller'ın _tkinter runtime hook'unu devre dışı bırakmak için kullanılır.
PyInstaller'ın modülü içe aktarması durumunda, dummy bir uygulama oluşturur.
"""

class DummyTkinter:
    def __getattr__(self, name):
        return self
    
    def __call__(self, *args, **kwargs):
        return self

# PyInstaller'ın runtime hook'u tarafından aranan modül isimleri
sys = DummyTkinter()
Tkinter = DummyTkinter()
tkinter = DummyTkinter()
_tkinter = DummyTkinter()
tk = DummyTkinter()
Tcl = DummyTkinter()
tcl = DummyTkinter()
Tk = DummyTkinter()

def TCL_LIBRARY():
    return "dummy"

def TK_LIBRARY():
    return "dummy" 
 
 
 