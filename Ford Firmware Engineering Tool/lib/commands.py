from .imports import *
 # ==================== KZB COMMANDS ====================
    
def kzb_browse_unpack_input(self):
    filename = filedialog.askopenfilename(
        title="Select KZB/KZBF Archive",
        filetypes=[("KZB files", "*.kzb"), ("KZBF files", "*.kzbf"), ("All files", "*.*")]
    )
    if filename:
        self.kzb_unpack_input.set(filename)

def kzb_browse_pack_input(self):
    dirname = filedialog.askdirectory(title="Select Directory to Pack")
    if dirname:
        self.kzb_pack_input.set(dirname)

def kzb_browse_pack_output(self):
    filename = filedialog.asksaveasfilename(
        title="Save Archive As",
        defaultextension=".kzb",
        filetypes=[("KZB files", "*.kzb"), ("All files", "*.*")]
    )
    if filename:
        self.kzb_pack_output.set(filename)

def kzb_log_to_widget(self, widget, message):
    self.log_queue.put((widget, message))

def kzb_update_progress_ui(self, progressbar, status_label, progress_label, files_label, 
                      current, total, message):
    self.progress_queue.put((progressbar, status_label, progress_label, files_label, 
                            current, total, message))

def kzb_unpack_file(self):
    input_file = self.kzb_unpack_input.get()
    if not input_file:
        messagebox.showerror("Error", "Please select an input file")
        return
    if not Path(input_file).exists():
        messagebox.showerror("Error", "Input file does not exist")
        return

    self.kzb_unpack_log.configure(state='normal')
    self.kzb_unpack_log.delete(1.0, tk.END)
    self.kzb_unpack_log.configure(state='disabled')
    self.kzb_unpack_progress['value'] = 0
    self.kzb_unpack_progress_label.configure(text="0%")
    self.kzb_unpack_files_label.configure(text="0/0")
    self.kzb_unpack_status_label.configure(text="Initializing extraction...")

    def run_unpack():
        try:
            def progress_callback(current, total, message):
                self.kzb_update_progress_ui(
                    self.kzb_unpack_progress,
                    self.kzb_unpack_status_label,
                    self.kzb_unpack_progress_label,
                    self.kzb_unpack_files_label,
                    current, total, message
                )

            processor = KZBProcessor(
                lambda msg: self.kzb_log_to_widget(self.kzb_unpack_log, msg),
                progress_callback
            )
            output_dir = processor.unpack(Path(input_file))
            
            self.kzb_log_to_widget(self.kzb_unpack_log, "=" * 70)
            self.kzb_log_to_widget(self.kzb_unpack_log, "[SUCCESS] Extraction completed")
            self.kzb_log_to_widget(self.kzb_unpack_log, f"[OUTPUT] {output_dir}")
            self.kzb_log_to_widget(self.kzb_unpack_log, f"[STATS ] {processor.processed_files} files extracted")
            self.kzb_log_to_widget(self.kzb_unpack_log, "=" * 70)
            
            self.kzb_update_progress_ui(
                self.kzb_unpack_progress,
                self.kzb_unpack_status_label,
                self.kzb_unpack_progress_label,
                self.kzb_unpack_files_label,
                100, 100, "Extraction complete"
            )
            
            self.after(0, lambda: messagebox.showinfo(
                "Extraction Complete", 
                f"Archive unpacked successfully\n\nOutput: {output_dir}\nFiles: {processor.processed_files}"
            ))
        except Exception as e:
            self.kzb_log_to_widget(self.kzb_unpack_log, "=" * 70)
            self.kzb_log_to_widget(self.kzb_unpack_log, f"[ERROR] {str(e)}")
            self.kzb_log_to_widget(self.kzb_unpack_log, "=" * 70)
            self.kzb_update_progress_ui(
                self.kzb_unpack_progress,
                self.kzb_unpack_status_label,
                self.kzb_unpack_progress_label,
                self.kzb_unpack_files_label,
                0, 100, "Error occurred"
            )
            self.after(0, lambda: messagebox.showerror(
                "Extraction Failed", 
                f"Error during unpacking:\n\n{str(e)}"
            ))

    threading.Thread(target=run_unpack, daemon=True).start()

def kzb_pack_file(self):
    input_dir = self.kzb_pack_input.get()
    output_file = self.kzb_pack_output.get()

    if not input_dir:
        messagebox.showerror("Error", "Please select an input directory")
        return
    if not output_file:
        messagebox.showerror("Error", "Please select an output file")
        return

    if not Path(input_dir).exists():
        messagebox.showerror("Error", "Input directory does not exist")
        return

    self.kzb_pack_log.configure(state='normal')
    self.kzb_pack_log.delete(1.0, tk.END)
    self.kzb_pack_log.configure(state='disabled')
    self.kzb_pack_progress['value'] = 0
    self.kzb_pack_progress_label.configure(text="0%")
    self.kzb_pack_files_label.configure(text="0/0")
    self.kzb_pack_status_label.configure(text="Initializing packing...")

    def run_pack():
        try:
            def progress_callback(current, total, message):
                self.kzb_update_progress_ui(
                    self.kzb_pack_progress,
                    self.kzb_pack_status_label,
                    self.kzb_pack_progress_label,
                    self.kzb_pack_files_label,
                    current, total, message
                )

            result = pack_kzb(
                Path(input_dir),
                Path(output_file),
                lambda msg: self.kzb_log_to_widget(self.kzb_pack_log, msg),
                progress_callback
            )
            
            if result == 0:
                self.kzb_log_to_widget(self.kzb_pack_log, "=" * 70)
                self.kzb_log_to_widget(self.kzb_pack_log, "[SUCCESS] Packing completed")
                self.kzb_log_to_widget(self.kzb_pack_log, f"[OUTPUT] {output_file}")
                self.kzb_log_to_widget(self.kzb_pack_log, "=" * 70)
                
                self.kzb_update_progress_ui(
                    self.kzb_pack_progress,
                    self.kzb_pack_status_label,
                    self.kzb_pack_progress_label,
                    self.kzb_pack_files_label,
                    100, 100, "Packing complete"
                )
                
                self.after(0, lambda: messagebox.showinfo(
                    "Packing Complete", 
                    f"Archive created successfully\n\nOutput: {output_file}"
                ))
            else:
                self.after(0, lambda: messagebox.showerror(
                    "Packing Failed", 
                    "Error during packing. Check log for details."
                ))
        except Exception as e:
            self.kzb_log_to_widget(self.kzb_pack_log, "=" * 70)
            self.kzb_log_to_widget(self.kzb_pack_log, f"[ERROR] {str(e)}")
            self.kzb_log_to_widget(self.kzb_pack_log, "=" * 70)
            self.kzb_update_progress_ui(
                self.kzb_pack_progress,
                self.kzb_pack_status_label,
                self.kzb_pack_progress_label,
                self.kzb_pack_files_label,
                0, 100, "Error occurred"
            )
            self.after(0, lambda: messagebox.showerror(
                "Packing Failed", 
                f"Error during packing:\n\n{str(e)}"
            ))

    threading.Thread(target=run_pack, daemon=True).start()

# ==================== VBF COMMANDS ====================

