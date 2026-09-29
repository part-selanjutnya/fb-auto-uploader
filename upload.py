import os
import json
import subprocess
import requests

# File konfigurasi
LINKS_FILE = "links.txt"
FB_PAGES_DATA = os.environ.get("FB_PAGES_DATA")

DEFAULT_CAPTION = """https://part-selanjutnya.github.io/part-selanjutnya/
Tonton selanjutnya☝️
#AlurCeritaFilm #ShortMovie #FilmPendek #CeritaSeru #DramaReels #CuplikanFilm #SinopsisFilm #RekomendasiFilm #FacebookReels #ReelsViral #FYPReels #ReelsIndonesia #VideoViral #TrendingReels"""

def download_video_yt_dlp(url, output_path="temp_video.mp4"):
    print(f"Mengunduh video via API: {url}")
    
    # 1. Menggunakan Cobalt API
    try:
        api_url = "https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "videoQuality": "720"
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        data = response.json()
        
        if "url" in data:
            video_url = data["url"]
            video_bytes = requests.get(video_url, timeout=60).content
            with open(output_path, "wb") as f:
                f.write(video_bytes)
            print("Berhasil mengunduh video via API!")
            return output_path
    except Exception as e:
        print(f"Peringatan API: {e}. Mengalihkan ke yt-dlp...")

    # 2. Fallback ke yt-dlp
    command = ["yt-dlp", "-o", output_path, "-f", "b[ext=mp4]/b", "--no-playlist", url]
    subprocess.run(command, check=True)
    return output_path
    
def upload_to_facebook_page(page_id, page_token, video_path):
    url = f"https://graph.facebook.com/v26.0/{page_id}/videos"
    payload = {
        'description': DEFAULT_CAPTION,
        'access_token': page_token
    }
    with open(video_path, 'rb') as video_file:
        files = {'source': video_file}
        print(f"Mengunggah ke Halaman ID: {page_id}...")
        response = requests.post(url, data=payload, files=files)
        return response.json()

def main():
    if not os.path.exists(LINKS_FILE):
        print("File links.txt tidak ditemukan.")
        return

    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    # Cari link pertama yang belum selesai (tidak diawali #DONE)
    target_index = -1
    target_url = ""
    for idx, line in enumerate(lines):
        if not line.startswith("#DONE"):
            target_index = idx
            target_url = line
            break

    if target_index == -1 or not target_url:
        print("Semua video di links.txt sudah selesai diposting!")
        return

    if not FB_PAGES_DATA:
        print("Error: Secret FB_PAGES_DATA tidak ditemukan.")
        return

    pages = json.loads(FB_PAGES_DATA)
    video_file = "temp_video.mp4"

    try:
        # 1. Download video secara temporary
        download_video_yt_dlp(target_url, video_file)

        # 2. Upload ke seluruh 10 Facebook Pages
        for page in pages:
            res = upload_to_facebook_page(page['id'], page['token'], video_file)
            print(f"Hasil {page['name']}: {res}")

        # 3. Tandai link yang sudah sukses diunggah
        lines[target_index] = f"#DONE {target_url}"
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")

        print("Berhasil mengunggah video ke semua halaman!")

    except Exception as e:
        print(f"Gagal memproses video: {e}")

    finally:
        # 4. Hapus file video temporary agar runner tetap bersih
        if os.path.exists(video_file):
            os.remove(video_file)

if __name__ == "__main__":
    main()
