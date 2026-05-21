import keyboard
import time

def start_mapping():
    print("=== KEYBOARD MAPPING TOOL ===")
    print("Instruksi:")
    print("1. Tekan tombol keyboardmu berurutan (Row 1 kiri -> kanan, lalu Row 2, dst).")
    print("2. Program akan mencatat Scan Code dan Nama Tombol.")
    print("3. Tekan 'ESC' agak lama untuk mengakhiri dan menyimpan.")
    print("--------------------------------------------------")

    recorded_keys = []
    
    def on_key_event(e):
        if e.event_type == 'down':
            # Simpan data unik: (Nama, Scan Code)
            key_data = f"Nama: {e.name} | Scan Code: {e.scan_code}"
            
            # Cek agar tidak dobel saat ditekan lama
            if not recorded_keys or recorded_keys[-1] != key_data:
                recorded_keys.append(key_data)
                print(f"Tercatat: {key_data}")

    # Mulai mendengarkan
    keyboard.hook(on_key_event)

    # Loop sampai dihentikan manual (Esc)
    try:
        while True:
            if keyboard.is_pressed('esc'):
                # Tunggu sebentar untuk memastikan user memang ingin keluar
                time.sleep(1)
                if keyboard.is_pressed('esc'):
                    break
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass

    # Simpan ke file
    with open("mapping_layout.txt", "w") as f:
        f.write("HASIL MAPPING KEYBOARD ANDA:\n")
        f.write("============================\n")
        for i, key in enumerate(recorded_keys):
            f.write(f"Key {i+1}: {key}\n")
    
    print("\n--------------------------------------------------")
    print(f"Selesai! {len(recorded_keys)} tombol telah disimpan di 'mapping_layout.txt'")
    print("Gunakan data tersebut untuk menyusun koordinat di kode UI utama.")

if __name__ == "__main__":
    start_mapping()