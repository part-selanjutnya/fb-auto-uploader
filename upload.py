import json
import os
import time
import requests


def download_video(url, output_path="temp_video.mp4"):
    """Mengunduh file video dari URL publik atau TikTok/Reels link."""
    print(f"Mengunduh video dari: {url}")
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(
            url, headers=headers, stream=True, timeout=30
        )
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        print("Berhasil mengunduh video.")
        return output_path
    except Exception as e:
        print(f"Gagal mengunduh video: {e}")
        return None


def upload_reels_to_facebook(
    page_name, page_id, page_token, video_path, caption="Automated Reels"
):
    """Mengunggah video ke Facebook Reels menggunakan 3-Step Resumable Upload API."""
    print(f"\nMengunggah REELS ke Halaman: {page_name} ({page_id})")

    # Step 1: Inisialisasi Sesi Upload
    init_url = f"https://graph.facebook.com/v26.0/{page_id}/video_reels"
    init_payload = {
        "upload_phase": "start",
        "access_token": page_token,
    }

    try:
        init_res = requests.post(init_url, data=init_payload).json()
        if "video_id" not in init_res or "upload_url" not in init_res:
            print(f"Gagal Inisialisasi pada {page_name}: {init_res}")
            return None

        video_id = init_res["video_id"]
        upload_url = init_res["upload_url"]

        # Step 2: Upload Binary Video
        file_size = os.path.getsize(video_path)
        headers = {
            "Authorization": f"OAuth {page_token}",
            "offset": "0",
            "file_size": str(file_size),
        }

        with open(video_path, "rb") as video_file:
            requests.post(upload_url, headers=headers, data=video_file)

        # Jeda sejenak untuk pemrosesan file di server Meta
        time.sleep(5)

        # Step 3: Finish & Publish
        publish_url = f"https://graph.facebook.com/v26.0/{page_id}/video_reels"
        publish_payload = {
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
            "access_token": page_token,
        }

        finish_res = requests.post(publish_url, data=publish_payload).json()
        print(f"Hasil Upload REELS {page_name}: {finish_res}")

        if finish_res.get("success") or "id" in finish_res:
            post_id = finish_res.get("id", video_id)
            return f"{page_name}: https://www.facebook.com/reel/{post_id}"
        else:
            return f"{page_name}: https://www.facebook.com/reel/{video_id}"

    except Exception as e:
        print(f"Terjadi kesalahan saat unggah ke {page_name}: {e}")
        return None


def main():
    input_file = "input_link.txt"

    if not os.path.exists(input_file):
        print(f"File {input_file} tidak ditemukan!")
        return

    with open(input_file, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    if not urls:
        print(f"URL Video tidak ditemukan di {input_file}")
        return

    fb_pages_json = os.environ.get("FB_PAGES_DATA")
    if not fb_pages_json:
        print("Environment variable FB_PAGES_DATA tidak ditemukan!")
        return

    try:
        pages = json.loads(fb_pages_json)
    except Exception as e:
        print(f"Gagal memuat JSON dari FB_PAGES_DATA: {e}")
        return

    for target_url in urls:
        temp_video_path = "temp_video.mp4"
        downloaded = download_video(target_url, temp_video_path)

        if downloaded and os.path.exists(temp_video_path):
            results = [target_url]

            for page in pages:
                page_name = page.get("name", "Unknown Page")
                # Mendukung pembacaan kunci 'id' maupun 'page_id'
                page_id = page.get("id") or page.get("page_id")
                # Mendukung pembacaan kunci 'token' maupun 'access_token'
                page_token = page.get("token") or page.get("access_token")

                if page_id and page_token:
                    res_link = upload_reels_to_facebook(
                        page_name,
                        page_id,
                        page_token,
                        temp_video_path,
                        caption=f"Reels Video {page_name}",
                    )
                    if res_link:
                        results.append(res_link)

            # Simpan atau update ke links.txt
            with open("links.txt", "w") as f:
                f.write("\n".join(results) + "\n")

            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)


if __name__ == "__main__":
    main()
