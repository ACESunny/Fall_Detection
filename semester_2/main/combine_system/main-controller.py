import os
import subprocess
import time
from threading import Thread
import tkinter as tk
from tkinter import ttk, messagebox

class ScriptController:
    def __init__(self):
        self.scripts = {
            'input.py': {'process': None, 'running': False, 'output': ''},
            'pose_detection.py': {'process': None, 'running': False, 'output': ''},
            'zone_detection.py': {'process': None, 'running': False, 'output': ''},
            'feature.py': {'process': None, 'running': False, 'output': ''},
            'notification.py': {'process': None, 'running': False, 'output': ''},
            'label.py': {'process': None, 'running': False, 'output': ''},
            'notification-for-window.py': {'process': None, 'running': False, 'output': ''}
        }
        
    def start_script(self, script_name):
        if script_name not in self.scripts:
            return False
            
        if not self.scripts[script_name]['running']:
            try:
                # Special handling for notification-for-window.py which might need Pythonw
                if script_name == 'notification-for-window.py':
                    process = subprocess.Popen(
                        ['pythonw', script_name],  # Use pythonw for no console window
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                else:
                    process = subprocess.Popen(
                        ['python', script_name],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1,
                        universal_newlines=True
                    )
                
                self.scripts[script_name]['process'] = process
                self.scripts[script_name]['running'] = True
                
                # Start thread to monitor output
                Thread(target=self.monitor_output, args=(script_name,), daemon=True).start()
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start {script_name}: {str(e)}")
                return False
        return False
    
    def stop_script(self, script_name):
        if script_name not in self.scripts:
            return False
            
        if self.scripts[script_name]['running']:
            try:
                process = self.scripts[script_name]['process']
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                self.scripts[script_name]['process'] = None
                self.scripts[script_name]['running'] = False
                return True
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop {script_name}: {str(e)}")
                return False
        return False
    
    def monitor_output(self, script_name):
        process = self.scripts[script_name]['process']
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                self.scripts[script_name]['output'] += output
        self.scripts[script_name]['running'] = False
    
    def get_status(self, script_name):
        if script_name in self.scripts:
            return self.scripts[script_name]['running']
        return False
    
    def get_output(self, script_name):
        if script_name in self.scripts:
            return self.scripts[script_name]['output']
        return ""

class ControllerGUI:
    def __init__(self, root):
        self.root = root
        self.controller = ScriptController()
        
        self.setup_ui()
    
    def setup_ui(self):
        self.root.title("Python Script Controller")
        self.root.geometry("1000x800")
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Script control frame
        control_frame = ttk.LabelFrame(main_frame, text="Script Controls", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Output frame
        output_frame = ttk.LabelFrame(main_frame, text="Script Output", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        # Notebook for multiple tabs
        self.notebook = ttk.Notebook(output_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs for each script
        self.output_texts = {}
        for script in self.controller.scripts.keys():
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=script)
            
            text = tk.Text(tab, wrap=tk.WORD)
            scrollbar = ttk.Scrollbar(text)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            text.config(yscrollcommand=scrollbar.set)
            scrollbar.config(command=text.yview)
            text.pack(fill=tk.BOTH, expand=True)
            
            self.output_texts[script] = text
        
        # Create controls for each script
        self.script_vars = {}
        self.script_buttons = {}
        
        # Organize scripts into categories
        script_categories = {
            "Input": ['input.py'],
            "Processing": ['pose_detection.py', 'zone_detection.py', 'feature.py'],
            "Output": ['notification.py', 'label.py', 'notification-for-window.py']
        }
        
        for category, scripts in script_categories.items():
            category_frame = ttk.LabelFrame(control_frame, text=category, padding="5")
            category_frame.pack(fill=tk.X, pady=5, padx=5)
            
            for script in scripts:
                # Status frame
                frame = ttk.Frame(category_frame)
                frame.pack(fill=tk.X, pady=2)
                
                # Script name label
                ttk.Label(frame, text=script, width=25).pack(side=tk.LEFT)
                
                # Status indicator
                status_var = tk.StringVar(value="Stopped")
                self.script_vars[script] = status_var
                ttk.Label(frame, textvariable=status_var, width=10).pack(side=tk.LEFT, padx=5)
                
                # Start button
                start_btn = ttk.Button(frame, text="Start", 
                                     command=lambda s=script: self.start_script(s))
                start_btn.pack(side=tk.LEFT, padx=2)
                
                # Stop button
                stop_btn = ttk.Button(frame, text="Stop", 
                                    command=lambda s=script: self.stop_script(s))
                stop_btn.pack(side=tk.LEFT, padx=2)
                
                # View output button
                output_btn = ttk.Button(frame, text="View Output", 
                                       command=lambda s=script: self.show_output(s))
                output_btn.pack(side=tk.LEFT, padx=2)
                
                self.script_buttons[script] = {'start': start_btn, 'stop': stop_btn}
                
                # Disable stop button initially
                stop_btn.config(state=tk.DISABLED)
        
        # Control buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Start all button
        ttk.Button(btn_frame, text="Start All", command=self.start_all).pack(side=tk.LEFT, padx=5)
        
        # Stop all button
        ttk.Button(btn_frame, text="Stop All", command=self.stop_all).pack(side=tk.LEFT, padx=5)
        
        # Clear output button
        ttk.Button(btn_frame, text="Clear All Output", command=self.clear_all_output).pack(side=tk.RIGHT, padx=5)
        
        # Update status periodically
        self.update_status()
    
    def start_script(self, script_name):
        if self.controller.start_script(script_name):
            self.script_vars[script_name].set("Running")
            self.script_buttons[script_name]['start'].config(state=tk.DISABLED)
            self.script_buttons[script_name]['stop'].config(state=tk.NORMAL)
            self.append_output(script_name, f"{script_name} started\n")
    
    def stop_script(self, script_name):
        if self.controller.stop_script(script_name):
            self.script_vars[script_name].set("Stopped")
            self.script_buttons[script_name]['start'].config(state=tk.NORMAL)
            self.script_buttons[script_name]['stop'].config(state=tk.DISABLED)
            self.append_output(script_name, f"{script_name} stopped\n")
    
    def start_all(self):
        for script in self.controller.scripts.keys():
            if not self.controller.get_status(script):
                self.start_script(script)
    
    def stop_all(self):
        for script in self.controller.scripts.keys():
            if self.controller.get_status(script):
                self.stop_script(script)
    
    def show_output(self, script_name):
        output = self.controller.get_output(script_name)
        self.output_texts[script_name].delete(1.0, tk.END)
        self.output_texts[script_name].insert(tk.END, f"=== Output for {script_name} ===\n")
        self.output_texts[script_name].insert(tk.END, output)
        self.notebook.select([tab for tab in self.notebook.tabs() 
                            if self.notebook.tab(tab, "text") == script_name][0])
    
    def append_output(self, script_name, text):
        self.output_texts[script_name].insert(tk.END, text)
        self.output_texts[script_name].see(tk.END)
    
    def clear_all_output(self):
        for script in self.controller.scripts.keys():
            self.output_texts[script].delete(1.0, tk.END)
    
    def update_status(self):
        for script in self.controller.scripts.keys():
            if self.controller.get_status(script):
                self.script_vars[script].set("Running")
                self.script_buttons[script]['start'].config(state=tk.DISABLED)
                self.script_buttons[script]['stop'].config(state=tk.NORMAL)
            else:
                self.script_vars[script].set("Stopped")
                self.script_buttons[script]['start'].config(state=tk.NORMAL)
                self.script_buttons[script]['stop'].config(state=tk.DISABLED)
        
        # Update output for all running scripts
        for script in self.controller.scripts.keys():
            if self.controller.get_status(script):
                output = self.controller.get_output(script)
                if output and output != self.output_texts[script].get("1.0", tk.END):
                    self.append_output(script, output)
                    self.controller.scripts[script]['output'] = ''  # Clear buffer
        
        self.root.after(1000, self.update_status)

if __name__ == "__main__":
    root = tk.Tk()
    app = ControllerGUI(root)
    root.mainloop()