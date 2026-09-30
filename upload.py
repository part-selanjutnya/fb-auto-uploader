import json
import os
import time
import requests


def download_video(video_url, output_path="temp_video.mp4"):
    """Mengunduh video dari URL (misal: TikTok/Direct Link) dan menyimpannya secara lokal."""
    print(f"Mengunduh video dari: {video_url}")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(video_url, headers=headers, stream=True)
    if response.status_code == 200:
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
        print("Berhasil mengunduh video")
        return output_path
    else:
        print(f"Gagal mengunduh video. Status code: {response.status_code}")
        return None


def upload_reels_to_facebook(
    page_id, page_token, video_path, caption="Automated Reels Video"
):
    """Mengunggah video ke Facebook Reels menggunakan 3-Step Resumable Upload API."""
    print(f"Mengunggah REELS ke Halaman ID: {page_id}")

    # Step 1: Start Upload Session (Inisialisasi)
    init_url = f"https://graph.facebook.com/v20.0/{page_id}/video_reels"
    init_payload = {
        "upload_phase": "start",
        "access_token": page_token,
    }

    init_res = requests.post(init_url, data=init_payload).json()

    if "video_id" not in init_res or "upload_url" not in init_res:
        print(f"Hasil Upload REELS ke Halaman ID: {page_id} ***error: {init_res}***")
        return None

    video_id = init_res["video_id"]
    upload_url = init_res["upload_url"]

    # Step 2: Upload File Binary Video ke upload_url
    file_size = os.path.getsize(video_path)
    headers = {
        "Authorization": f"OAuth {page_token}",
        "offset": "0",
        "file_size": str(file_size),
    }

    with open(video_path, "rb") as video_file:
        upload_res = requests.post(
            upload_url, headers=headers, data=video_file
        ).json()

    # Step 3: Finish Upload & Publish
    # Memberikan jeda waktu (sleep) agar server Facebook selesai memproses encoding video
    time.sleep(10)

    publish_url = f"https://graph.facebook.com/v20.0/{page_id}/video_reels"
    publish_payload = {
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": caption,
        "access_token": page_token,
    }

    finish_res = requests.post(publish_url, data=publish_payload).json()
    print(
        f"Hasil Upload REELS ke Halaman ID: {page_id} ***response: {finish_res}***"
    )

    if finish_res.get("success") or "id" in finish_res:
        post_id = finish_res.get("id", video_id)
        return f"https://www.facebook.com/reel/{post_id}"
    else:
        return None


def main():
    # Ambil JSON FB Pages dari GitHub Secrets / Environment Variable
    fb_pages_json = os.environ.get("FB_PAGES_DATA")
    if not fb_pages_json:
        print("Error: Environment variable FB_PAGES_DATA tidak ditemukan.")
        return

    try:
        pages = json.loads(fb_pages_json)
    except Exception as e:
        print(f"Error parsing FB_PAGES_DATA JSON: {e}")
        return

    # Baca URL video dari file input (misal: input_link.txt atau url hardcoded)
    video_url = ""
    if os.path.exists("input_link.txt"):
        with open("input_link.txt", "r") as f:
            video_url = f.read().strip()

    if not video_url:
        print("URL Video tidak ditemukan di input_link.txt")
        return

    # Download file video
    local_video_file = download_video(video_url, "video_to_upload.mp4")
    if not local_video_file:
        return

    uploaded_links = []

    # Iterasi upload ke seluruh Halaman
    for page in pages:
        page_name = page.get("name", "Unknown")
        page_id = page.get("id")
        token = page.get("token")

        if not page_id or not token:
            print(f"Data Halaman {page_name} tidak lengkap, dilewati.")
            continue

        reel_url = upload_reels_to_facebook(
            page_id,
            token,
            local_video_file,
            caption=f"Video Reels {page_name}",
        )
        if reel_url:
            uploaded_links.append(f"{page_name}: {reel_url}")

    # Simpan hasil link yang berhasil diunggah ke file links.txt
    if uploaded_links:
        with open("links.txt", "a") as f:
            f.write("\n".join(uploaded_links) + "\n")

    # Bersihkan file video sementara
    if os.path.exists(local_video_file):
        os.remove(local_video_file)


if __name__ == "__main__":
    main()
