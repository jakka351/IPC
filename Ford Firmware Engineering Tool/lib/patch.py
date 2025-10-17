#!/usr/bin/env python3
"""
Auto-Patcher: Converts 2-image Image Utility to 6-image version
Automatically loads 3 uploaded sprite images on startup

Usage:
    python3 patch_to_6_images.py input_file.py output_file.py
    
Or run directly:
    python3 patch_to_6_images.py
    (will look for tool.py and create tool_modified.py)
"""

import sys
import re
from pathlib import Path


def apply_patches(content: str) -> str:
    """Apply all necessary patches to convert to 6-image support"""
    
    print("Applying patches...")
    
    # PATCH 1: Replace Image Utility state variables in __init__
    print("  [1/7] Updating state variables...")
    pattern1 = r'(        # Image Utility state\n)'  \
               r'(        self\.img1_original.*?\n)'  \
               r'(        self\.img2_original.*?\n)'  \
               r'(        self\.img1_current.*?\n)'  \
               r'(        self\.img2_current.*?\n)'  \
               r'(        self\.img1_path.*?\n)'  \
               r'(        self\.img2_path.*?\n)'  \
               r'(        self\.img1_display.*?\n)'  \
               r'(        self\.img2_display.*?\n)'
    
    replacement1 = '''        # Image Utility state - MODIFIED TO SUPPORT 6 IMAGES
        self.img_original: List[Optional[Image.Image]] = [None] * 6
        self.img_current: List[Optional[Image.Image]] = [None] * 6
        self.img_path: List[Optional[Path]] = [None] * 6
        self.img_display: List[Optional[ImageTk.PhotoImage]] = [None] * 6
        self.img_canvas: List[Optional[tk.Canvas]] = [None] * 6
        self.img_info: List[Optional[ttk.Label]] = [None] * 6
'''
    
    content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)
    
    # PATCH 2: Add auto-load call after _tick_ui()
    print("  [2/7] Adding auto-load functionality...")
    pattern2 = r'(        self\._tick_ui\(\))'
    replacement2 = r'\1\n        \n        # Auto-load startup images\n        self.after(100, self._load_startup_images)'
    content = re.sub(pattern2, replacement2, content)
    
    # PATCH 3: Add _load_startup_images method (insert after __init__)
    print("  [3/7] Adding _load_startup_images method...")
    new_method = '''
    def _load_startup_images(self):
        """Load the three uploaded images into slots 0, 1, and 2"""
        startup_images = [
            "/mnt/user-data/uploads/1760647562196_S550_Sprite_01.png",
            "/mnt/user-data/uploads/1760647562197_S550_Sprite_02.png",
            "/mnt/user-data/uploads/1760647562197_S550_Sprite_03.png"
        ]
        
        for idx, img_path in enumerate(startup_images):
            if Path(img_path).exists():
                try:
                    img = Image.open(img_path)
                    self.img_original[idx] = img.copy()
                    self.img_current[idx] = img.copy()
                    self.img_path[idx] = Path(img_path)
                    self._update_image_display(idx)
                except Exception as e:
                    print(f"Failed to load startup image {idx + 1}: {e}")
        
        self.status_label.configure(text="Status: Loaded 3 startup images into slots 1-3")
'''
    
    # Find a good insertion point (after __init__ method)
    pattern3 = r'(    def _build_ui\(self\):)'
    replacement3 = new_method + r'\n\1'
    content = re.sub(pattern3, replacement3, content, count=1)
    
    # PATCH 4-5: Replace _build_image_utility_ui and add _create_image_panel
    print("  [4/7] Replacing _build_image_utility_ui method...")
    print("  [5/7] Adding _create_image_panel method...")
    
    # Find and replace the entire _build_image_utility_ui method
    pattern_build = r'    def _build_image_utility_ui\(self, parent\):.*?(?=\n    def |\n# =====|\Z)'
    
    new_build_method = '''    def _build_image_utility_ui(self, parent):
        """Build the Image Utility UI with 6 image slots in a 2x3 grid"""
        # Title
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(title_frame, text="Image Utility - 6 Image Editor", 
                 font=('TkDefaultFont', 12, 'bold')).pack(anchor='w')
        ttk.Label(title_frame, text="Display and edit up to 6 PNG images simultaneously", 
                 font=('TkDefaultFont', 9), foreground='gray').pack(anchor='w')
        
        ttk.Separator(parent, orient='horizontal').pack(fill='x', pady=(0, 15))
        
        # Create 2 rows of 3 images each
        for row in range(2):
            row_frame = ttk.Frame(parent)
            row_frame.pack(fill='both', expand=True, pady=5)
            
            for col in range(3):
                img_num = row * 3 + col
                self._create_image_panel(row_frame, img_num)

    def _create_image_panel(self, parent, img_num: int):
        """Create a single image panel for the specified slot"""
        panel = ttk.LabelFrame(parent, text=f"Image {img_num + 1}", padding="5")
        panel.pack(side='left', fill='both', expand=True, padx=5)
        
        # Control buttons
        ctrl_frame = ttk.Frame(panel)
        ctrl_frame.pack(fill='x', pady=(0, 5))
        
        ttk.Button(ctrl_frame, text="Load", 
                  command=lambda: self.img_load(img_num), width=8).pack(side='left', padx=2)
        ttk.Button(ctrl_frame, text="Save", 
                  command=lambda: self.img_save(img_num), width=8).pack(side='left', padx=2)
        ttk.Button(ctrl_frame, text="Clear", 
                  command=lambda: self.img_clear(img_num), width=8).pack(side='left', padx=2)
        
        # Image display canvas
        canvas_frame = ttk.Frame(panel, relief='sunken', borderwidth=1)
        canvas_frame.pack(fill='both', expand=True, pady=(0, 5))
        
        canvas = tk.Canvas(canvas_frame, bg='gray90', width=300, height=250)
        canvas.pack(fill='both', expand=True)
        self.img_canvas[img_num] = canvas
        
        # Image info label
        info = ttk.Label(panel, text="No image loaded", relief='sunken')
        info.pack(fill='x', pady=(0, 5))
        self.img_info[img_num] = info
        
        # Edit controls in a compact layout
        edit_frame = ttk.LabelFrame(panel, text="Edit", padding="3")
        edit_frame.pack(fill='x')
        
        # Row 1: Rotate, Flip
        row1 = ttk.Frame(edit_frame)
        row1.pack(fill='x', pady=1)
        ttk.Button(row1, text="Rotate 90°", 
                  command=lambda: self.img_rotate(img_num, 90), width=9).pack(side='left', padx=1)
        ttk.Button(row1, text="Flip H", 
                  command=lambda: self.img_flip(img_num, 'h'), width=9).pack(side='left', padx=1)
        ttk.Button(row1, text="Flip V", 
                  command=lambda: self.img_flip(img_num, 'v'), width=9).pack(side='left', padx=1)
        
        # Row 2: Effects
        row2 = ttk.Frame(edit_frame)
        row2.pack(fill='x', pady=1)
        ttk.Button(row2, text="Resize...", 
                  command=lambda: self.img_resize_dialog(img_num), width=9).pack(side='left', padx=1)
        ttk.Button(row2, text="Grayscale", 
                  command=lambda: self.img_grayscale(img_num), width=9).pack(side='left', padx=1)
        ttk.Button(row2, text="Blur", 
                  command=lambda: self.img_blur(img_num), width=9).pack(side='left', padx=1)

'''
    
    content = re.sub(pattern_build, new_build_method, content, flags=re.DOTALL)
    
    # PATCH 6: Update all img_* methods
    print("  [6/7] Updating image manipulation methods...")
    
    # img_load
    content = re.sub(
        r'    def img_load\(self, img_num: int\):.*?(?=\n    def )',
        r'''    def img_load(self, img_num: int):
        """Load an image into the specified slot"""
        filename = filedialog.askopenfilename(
            title=f"Load Image {img_num + 1}",
            filetypes=[
                ("PNG images", "*.png"),
                ("All image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All files", "*.*")
            ]
        )
        if not filename:
            return
        
        try:
            img = Image.open(filename)
            self.img_original[img_num] = img.copy()
            self.img_current[img_num] = img.copy()
            self.img_path[img_num] = Path(filename)
            self._update_image_display(img_num)
            
            self.status_label.configure(text=f"Status: Loaded image {img_num + 1} - {Path(filename).name}")
            
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load image:\\n\\n{str(e)}")

''',
        content, flags=re.DOTALL
    )
    
    # img_save
    content = re.sub(
        r'    def img_save\(self, img_num: int\):.*?(?=\n    def )',
        r'''    def img_save(self, img_num: int):
        """Save the image from the specified slot"""
        img = self.img_current[img_num]
        
        if img is None:
            messagebox.showwarning("No Image", f"No image loaded in slot {img_num + 1}")
            return
        
        filename = filedialog.asksaveasfilename(
            title=f"Save Image {img_num + 1}",
            defaultextension=".png",
            filetypes=[
                ("PNG images", "*.png"),
                ("JPEG images", "*.jpg"),
                ("All files", "*.*")
            ]
        )
        if not filename:
            return
        
        try:
            img.save(filename)
            self.status_label.configure(text=f"Status: Saved image {img_num + 1} - {Path(filename).name}")
            messagebox.showinfo("Success", f"Image saved successfully!\\n\\n{filename}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save image:\\n\\n{str(e)}")

''',
        content, flags=re.DOTALL
    )
    
    # img_clear
    content = re.sub(
        r'    def img_clear\(self, img_num: int\):.*?(?=\n    def )',
        r'''    def img_clear(self, img_num: int):
        """Clear the image from the specified slot"""
        self.img_original[img_num] = None
        self.img_current[img_num] = None
        self.img_path[img_num] = None
        self.img_display[img_num] = None
        
        if self.img_canvas[img_num]:
            self.img_canvas[img_num].delete("all")
        if self.img_info[img_num]:
            self.img_info[img_num].configure(text="No image loaded")
        
        self.status_label.configure(text=f"Status: Cleared image {img_num + 1}")

''',
        content, flags=re.DOTALL
    )
    
    # img_rotate
    content = re.sub(
        r'    def img_rotate\(self, img_num: int, angle: int\):.*?(?=\n    def )',
        r'''    def img_rotate(self, img_num: int, angle: int):
        """Rotate the image in the specified slot"""
        img = self.img_current[img_num]
        
        if img is None:
            messagebox.showwarning("No Image", f"No image loaded in slot {img_num + 1}")
            return
        
        rotated = img.rotate(angle, expand=True)
        self.img_current[img_num] = rotated
        self._update_image_display(img_num)
        self.status_label.configure(text=f"Status: Rotated image {img_num + 1} by {angle}°")

''',
        content, flags=re.DOTALL
    )
    
    # img_flip
    content = re.sub(
        r'    def img_flip\(self, img_num: int, direction: str\):.*?(?=\n    def )',
        r'''    def img_flip(self, img_num: int, direction: str):
        """Flip the image in the specified slot"""
        img = self.img_current[img_num]
        
        if img is None:
            messagebox.showwarning("No Image", f"No image loaded in slot {img_num + 1}")
            return
        
        if direction == 'h':
            flipped = img.transpose(Image.FLIP_LEFT_RIGHT)
            desc = "horizontally"
        else:
            flipped = img.transpose(Image.FLIP_TOP_BOTTOM)
            desc = "vertically"
        
        self.img_current[img_num] = flipped
        self._update_image_display(img_num)
        self.status_label.configure(text=f"Status: Flipped image {img_num + 1} {desc}")

''',
        content, flags=re.DOTALL
    )
    
    # img_resize_dialog, img_grayscale, img_blur, and _update_image_display
    # (Similar pattern - replacing self.img1_* with self.img_*[img_num])
    
    print("  [7/7] Updating image display method...")
    content = re.sub(
        r'    def _update_image_display\(self, img_num: int\):.*?(?=\n    def |\Z)',
        r'''    def _update_image_display(self, img_num: int):
        """Update the display for the specified image slot"""
        img = self.img_current[img_num]
        canvas = self.img_canvas[img_num]
        info_label = self.img_info[img_num]
        
        if img is None or canvas is None:
            return
        
        # Get canvas size
        canvas.update_idletasks()
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        if canvas_width <= 1:
            canvas_width = 300
        if canvas_height <= 1:
            canvas_height = 250
        
        # Calculate scaling to fit canvas
        img_width, img_height = img.size
        scale = min(canvas_width / img_width, canvas_height / img_height, 1.0)
        
        display_width = int(img_width * scale)
        display_height = int(img_height * scale)
        
        # Resize for display
        display_img = img.resize((display_width, display_height), Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        photo = ImageTk.PhotoImage(display_img)
        
        # Store reference to prevent garbage collection
        self.img_display[img_num] = photo
        
        # Display on canvas
        canvas.delete("all")
        x = (canvas_width - display_width) // 2
        y = (canvas_height - display_height) // 2
        canvas.create_image(x, y, anchor='nw', image=photo)
        
        # Update info label
        if info_label:
            info_label.configure(text=f"{img.width}x{img.height} | {img.mode}")

''',
        content, flags=re.DOTALL
    )
    
    # Update remaining methods (img_resize_dialog, img_grayscale, img_blur)
    content = _update_remaining_methods(content)
    
    print("\n✓ All patches applied successfully!")
    return content


def _update_remaining_methods(content: str) -> str:
    """Update the remaining image methods that weren't caught by the main patterns"""
    
    # img_resize_dialog
    content = re.sub(
        r'def img_resize_dialog\(self, img_num: int\):.*?self\.status_label\.configure\(text=f"Status: Resized image \{img_num \+ 1\}.*?\)',
        lambda m: m.group(0).replace('self.img1_current', 'self.img_current[img_num]')
                           .replace('self.img2_current', 'self.img_current[img_num]'),
        content, flags=re.DOTALL
    )
    
    # img_grayscale
    content = re.sub(
        r'def img_grayscale\(self, img_num: int\):.*?self\.status_label\.configure\(text=f"Status: Converted image \{img_num \+ 1\}',
        lambda m: m.group(0).replace('self.img1_current', 'self.img_current[img_num]')
                           .replace('self.img2_current', 'self.img_current[img_num]'),
        content, flags=re.DOTALL
    )
    
    # img_blur
    content = re.sub(
        r'def img_blur\(self, img_num: int\):.*?self\.status_label\.configure\(text=f"Status: Applied blur to image \{img_num \+ 1\}',
        lambda m: m.group(0).replace('self.img1_current', 'self.img_current[img_num]')
                           .replace('self.img2_current', 'self.img_current[img_num]'),
        content, flags=re.DOTALL
    )
    
    return content


def main():
    """Main function to run the patcher"""
    
    print("=" * 70)
    print("Ford Firmware Tool - 6-Image Patcher")
    print("=" * 70)
    print()
    
    # Determine input and output files
    if len(sys.argv) >= 3:
        input_file = Path(sys.argv[1])
        output_file = Path(sys.argv[2])
    elif len(sys.argv) == 2:
        input_file = Path(sys.argv[1])
        output_file = input_file.parent / f"{input_file.stem}_modified{input_file.suffix}"
    else:
        # Default names
        input_file = Path("tool.py")
        output_file = Path("tool_modified.py")
        
        print(f"No arguments provided. Using defaults:")
        print(f"  Input:  {input_file}")
        print(f"  Output: {output_file}")
        print()
    
    # Check if input file exists
    if not input_file.exists():
        print(f"❌ Error: Input file '{input_file}' not found!")
        print()
        print("Usage:")
        print(f"  {sys.argv[0]} input_file.py output_file.py")
        print(f"  {sys.argv[0]} input_file.py  (creates input_file_modified.py)")
        print(f"  {sys.argv[0]}  (looks for tool.py, creates tool_modified.py)")
        return 1
    
    print(f"Reading: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return 1
    
    print(f"Original file: {len(original_content)} characters, {len(original_content.split(chr(10)))} lines")
    print()
    
    # Apply patches
    try:
        modified_content = apply_patches(original_content)
    except Exception as e:
        print(f"\n❌ Error applying patches: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print()
    print(f"Modified file: {len(modified_content)} characters, {len(modified_content.split(chr(10)))} lines")
    print()
    
    # Write output file
    print(f"Writing: {output_file}")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(modified_content)
    except Exception as e:
        print(f"❌ Error writing file: {e}")
        return 1
    
    print()
    print("=" * 70)
    print("✓ Patching complete!")
    print("=" * 70)
    print()
    print("Changes made:")
    print("  • Image slots increased from 2 to 6 (2x3 grid layout)")
    print("  • Auto-loads 3 uploaded S550 sprite images on startup")
    print("  • All image manipulation methods updated")
    print("  • Compact panel design for better space utilization")
    print()
    print(f"Run your modified tool with: python3 {output_file}")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
