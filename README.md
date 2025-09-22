# 📸 Photobooth – Client & Server System

This project consists of two main components:

- **`clientside/`** – The software running on the physical photobox (e.g. Raspberry Pi + DSLR).
- **`serverside/`** – The minimalistic web interface for accessing photos via QR code.

---

## 🧠 Concept

1. **The Photobox (Client)**
   - Takes a photo when a physical button is pressed (e.g. Touchscreen).
   - Automatically generates a random alphanumeric **token** in the format `ABCD-EFGH`.
   - Saves the photo locally using this token as the filename.
   - Displays the image and a QR code linking to the photo.
   - Uploads the photo **passwordlessly via SCP** to the web server (`serverside/bilder/`).
   - The final URL format (QR code) looks like:
     ```
     https://www.fotobox.kreisaaron.de/?code=ABCD-EFGH
     ```

2. **The Server (Website)**
   - Hosts a minimalist, static website.
   - When a token is provided via `?code=...`, it loads the corresponding image (e.g. `bilder/ABCD-EFGH.jpg`).
   - No user authentication or image gallery – images are only accessible if you have the exact token.
   - Directory listing is disabled using `.htaccess`.
   - The page is fully **client-side**, with no backend logic.
   - Due to `robots.txt` search-engines don't index the `/bilder` folder.

---

## 🖥️ `clientside/` – Photobox Software

- Written in **Python** (with Tkinter GUI).
- Uses `gphoto2` to communicate with DSLR cameras (e.g. Nikon D5600).
- Displays a countdown, takes the photo, then shows a QR code linked to the uploaded image.
- Example filename: `fotobox/ABCD-EFGH.jpg`
- Uploads with:
  ```bash
  scp fotobox/ABCD-EFGH.jpg user@server:/var/www/fotobox/bilder/
  ```
## Dependencies:  
- python3
- tkinter
- Pillow
- qrcode
- gphoto2
- openssh-client

## 🌐 `serverside/` – Website
- Static HTML/CSS + `.htaccess` configuration.
- Core files:
  - `index.html`: Displays image if a valid token is provided.
  - `impressum.html`, `datenschutz.html`: Legal pages for GDPR compliance.
  - `.htaccess`: Disables directory listing, allows only known file access.

## 🛠️ Setup & Notes
- The photobooth requires a stable internet connection.
- Passwordless SSH must be configured for automatic uploads.
- The `/bilder` folder should be protected using `.htaccess`.
- Camera should be set to **P** or **M** mode.
