import tkinter as tk
import threading

def type_on_keyboard(input: str) -> str:
  output = f"Успешный вывод строки: {input}"
  print(output)

  return output

import tkinter as tk
import threading

def show_red_screen(situation: str, location: str):
    root = tk.Tk()
    root.title("Emergency Alert")
    root.geometry("1280x720")
    root.configure(bg='red')

    label = tk.Label(root, text=f"SITUATION: {situation}\nLOCATION: {location}", 
                     font=("Helvetica", 36), fg="white", bg="red")
    label.pack(expand=True)

    root.after(0, lambda: root.lift())  # Bring window to front
    root.mainloop()

def ping_emergency(situation: str, location: str) -> str:
    output = "Вызов тревогу выполнен успешно."
    
    # Run the red screen in a separate thread to avoid blocking
    threading.Thread(target=show_red_screen, args=(situation, location), daemon=True).start()
    
    return output