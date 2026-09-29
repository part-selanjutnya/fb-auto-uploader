import os
import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LINKS_FILE = "links.txt"
FB_PAGES_DATA = os.environ.get("FB_PAGES_DATA")

DEFAULT_CAPTION = """https://part-selanjutnya.github.io/part-selanjutnya/
Tonton selanjutnya☝️
#AlurCeritaFilm #ShortMovie #FilmPendek #CeritaSeru #DramaReels #CuplikanFilm #SinopsisFilm #RekomendasiFilm #FacebookReels #ReelsViral #FYPReels #ReelsIndonesia #VideoViral #TrendingReels"""

def download_video_via_api(url, output_path="temp_video.mp4"):
    print(f"Mengunduh video dari: {url}")
    session = requests.Session()
    session.verify = False
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Referer": "https://www.tikwm.com/"
    }
    try:
        res_head = session.get(url, headers=headers, allow_redirects=True, timeout=15)
        clean_url = res_head.url
    except Exception:
        clean_url = url

    # TikWM POST API
    try:
        api_url = "https://www.tikwm.com/api/"
        payload = {"url": clean_url, "count": 12, "cursor": 0, "web": 1, "hd": 1}
        res = session.post(api_url, data=payload, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            video_url = data.get("data", {}).get("play") or data.get("data", {}).get("wmplay")
            if video_url:
                if not video_url.startswith("http"):
                    video_url = f"https://www.tikwm.com{video_url}"
                video_bytes = session.get(video_url, headers=headers, timeout=90).content
                with open(output_path, "wb") as f:
                    f.write(video_bytes)
                print("Berhasil mengunduh video!")
                return output_path
    except Exception as e:
        print(f"Gagal mengunduh: {e}")

    raise Exception("Gagal mengunduh video dari API.")

def upload_as_facebook_reel(page_id, page_token, video_path):
    print(f"Mengunggah REELS ke Halaman ID: {page_id}...")
    
    # Step 1: Inisialisasi Upload Session Reels
    init_url = f"https://graph.facebook.com/v26.0/{page_id}/video_reels"
    init_payload = {
        'upload_phase': 'start',
        'access_token': page_token
    }
    init_res = requests.post(init_url, data=init_payload).json()
    video_id = init_res.get('video_id')
    upload_url = init_res.get('upload_url')

    if not video_id or not upload_url:
        print(f"Gagal inisialisasi Reels untuk {page_id}: {init_res}")
        return init_res

    # Step 2: Upload File Video ke Ruang Beralamat
    with open(video_path, 'rb') as f:
        video_data = f.read()
    
    upload_headers = {
        'Authorization': f'OAuth {page_token}',
        'offset': '0',
        'file_size': str(len(video_data))
    }
    upload_res = requests.post(upload_url, headers=upload_headers, data=video_data)

    # Step 3: Publikasikan Video sebagai REELS
    publish_payload = {
        'upload_phase': 'finish',
        'video_state': 'PUBLISHED',
        'description': DEFAULT_CAPTION,
        'access_token': page_token
    }
    final_res = requests.post(init_url, data=publish_payload).json()
    return final_res

def main():
    if not os.path.exists(LINKS_FILE):
        return

    with open(LINKS_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    target_index = -1
    target_url = ""
    for idx, line in enumerate(lines):
        if not line.startswith("#DONE"):
            target_index = idx
            target_url = line
            break

    if target_index == -1 or not target_url or not FB_PAGES_DATA:
        return

    pages = json.loads(FB_PAGES_DATA)
    video_file = "temp_video.mp4"

    try:
        download_video_via_api(target_url, video_file)

        for page in pages:
            res = upload_as_facebook_reel(page['id'], page['token'], video_file)
            print(f"Hasil Upload REELS [{page.get('name', page['id'])}]: {res}")

        lines[target_index] = f"#DONE {target_url}"
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines) + "\n")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if os.path.exists(video_file):
            os.remove(video_file)

if __name__ == "__main__":
    main()
