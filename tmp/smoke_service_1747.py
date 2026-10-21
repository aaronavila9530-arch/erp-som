import sys
import time
import tkinter as tk
from unittest.mock import patch, Mock

sys.path.insert(0, r'C:\Users\aaron\Documents\som-release-1.7.47')
from Modulos.Servicios.popup_servicio import PopupServicio

root = tk.Tk()
root.withdraw()
beats = []
def heartbeat():
    beats.append(time.monotonic())
    root.after(10, heartbeat)
def slow_credit(*args, **kwargs):
    time.sleep(0.3)
    return {}
def slow_save(data):
    time.sleep(0.3)
    return {'status': 'OK'}
try:
    with patch.object(PopupServicio, 'load_initial_data'), patch.object(
        PopupServicio, '_validate_required_fields', return_value=('2026-10-20', '12:00')
    ), patch('Modulos.Servicios.popup_servicio.check_order_to_cash_credit_api', side_effect=slow_credit) as credit, patch(
        'Modulos.Servicios.popup_servicio.post_servicio', side_effect=slow_save
    ) as post, patch('Modulos.Servicios.popup_servicio.messagebox') as messages:
        ui = PopupServicio(root, Mock())
        ui.withdraw()
        ui.honorarios.insert(0, '100')
        ui.costo_operativo.insert(0, '10')
        root.after(0, heartbeat)
        ui.save()
        ui.save()
        deadline = time.monotonic() + 4
        while ui.winfo_exists() and time.monotonic() < deadline:
            root.update()
            time.sleep(0.005)
        assert not ui.winfo_exists(), 'Save did not finish'
        assert len(beats) >= 20, len(beats)
        credit.assert_called_once()
        post.assert_called_once()
        messages.showinfo.assert_called_once()
        messages.showerror.assert_not_called()
        print('PASS: real Tk event loop responsive during slow credit/save; double save sends once; success closes dialog.')
finally:
    root.destroy()
