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

def download_video_via_api(url, output_path="temp_video.mp4"):
    print(f"Mengunduh video dari: {url}")
    
    # Resolusi shortlink jika berupa vt.tiktok.com atau s.snackvideo.com
    session = requests.Session()
    try:
        res_head = session.head(url, allow_redirects=True, timeout=15)
        clean_url = res_head.url
    except Exception:
        clean_url = url
    print(f"URL target teresolusi: {clean_url}")

    # 1. Unduh via TikWM API (Khusus TikTok - Tanpa Watermark)
    if "tiktok.com" in clean_url or "tiktok.com" in url:
        try:
            print("Mengunduh via TikWM API...")
            api_url = "https://www.tikwm.com/api/"
            payload = {"url": clean_url, "hd": 1}
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
            res = requests.post(api_url, data=payload, headers=headers, timeout=20).json()
            
            video_url = res.get("data", {}).get("play")
            if video_url:
                if not video_url.startswith("http"):
                    video_url = f"https://www.tikwm.com{video_url}"
                video_bytes = requests.get(video_url, timeout=90).content
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
                print("Berhasil mengunduh video TikTok tanpa watermark!")
                return output_path
        except Exception as e:
            print(f"TikWM API gagal: {e}. Mengalihkan ke fallback...")

    # 2. Fallback Universal via yt-dlp (Untuk platform lain)
    try:
        print("Mencoba fallback via yt-dlp...")
        command = [
            "yt-dlp",
            "-o", output_path,
            "-f", "b[ext=mp4]/b",
            "--no-playlist",
            clean_url
        ]
        subprocess.run(command, check=True)
        print("Berhasil mengunduh video via yt-dlp!")
        return output_path
    except Exception as e:
        print(f"yt-dlp gagal: {e}")

    raise Exception("Gagal mengunduh video dari semua metode yang tersedia.")

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
        print(f"Error: File {LINKS_FILE} tidak ditemukan.")
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
        print("Error: Secret FB_PAGES_DATA tidak ditemukan di environment variable.")
        return

    try:
        pages = json.loads(FB_PAGES_DATA)
    except Exception as e:
        print(f"Error: Gagal melakukan parse JSON pada FB_PAGES_DATA: {e}")
        return

    video_file = "temp_video.mp4"

    try:
        # 1. Download video
        download_video_via_api(target_url, video_file)

        # 2. Upload ke seluruh Facebook Pages yang terdaftar
        for page in pages:
            res = upload_to_facebook_page(page['id'], page['token'], video_file)
            print(f"Hasil Upload [{page.get('name', page['id'])}]: {res}")

        # 3. Tandai link yang berhasil diunggah dengan #DONE
        lines[target_index] = f"#DONE {target_url}"
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")

        print("Proses selesai! Video berhasil diposting dan links.txt diperbarui.")

    except Exception as e:
        print(f"Gagal memproses video: {e}")

    finally:
        # 4. Bersihkan file video temporary
        if os.path.exists(video_file):
            os.remove(video_file)

if __name__ == "__main__":
    main()
