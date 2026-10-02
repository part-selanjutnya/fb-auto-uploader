import json
import os
import re
import subprocess
import sys
import requests

# Memastikan modul gdown terinstall
try:
    import gdown
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gdown"])
    import gdown


def download_from_google_drive(url, output_path="temp_video.mp4"):
    print(f"Mengunduh file video dari Google Drive: {url}...")

    # Ekstrak File ID dari berbagai format URL Google Drive
    file_id = None
    match_d = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    match_id = re.search(r"id=([a-zA-Z0-9_-]+)", url)

    if match_d:
        file_id = match_d.group(1)
    elif match_id:
        file_id = match_id.group(1)

    # Unduh menggunakan ID atau URL langsung via gdown
    if file_id:
        gdown.download(id=file_id, output=output_path, quiet=False)
    else:
        gdown.download(url, output_path, quiet=False)

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(
            "Gagal mengunduh file video dari Google Drive. Periksa kembali izin akses link (harus 'Anyone with link')."
        )

    print("Unduhan berhasil.")
    return output_path


def upload_reels_to_page(page_id, page_token, file_path, caption):
    """Mengunggah video khusus ke Facebook Reels menggunakan 3-Step Resumable Upload API."""
    print(f"Mengunggah Reels ke halaman ID: {page_id}...")

    # Step 1: Inisialisasi Upload Session Reels
    init_url = f"https://graph.facebook.com/v20.0/{page_id}/video_reels"
    init_payload = {
        "upload_phase": "start",
        "access_token": page_token,
    }

    init_res = requests.post(init_url, data=init_payload).json()
    if "video_id" not in init_res or "upload_url" not in init_res:
        print(f" -> Gagal Inisialisasi Reels: {json.dumps(init_res)}")
        return init_res

    video_id = init_res["video_id"]
    upload_url = init_res["upload_url"]

    # Step 2: Transfer Binary File Video
    file_size = os.path.getsize(file_path)
    headers = {
        "Authorization": f"OAuth {page_token}",
        "offset": "0",
        "file_size": str(file_size),
    }

    with open(file_path, "rb") as f:
        requests.post(upload_url, headers=headers, data=f)

    # Step 3: Finish & Dipublikasikan sebagai Reel
    finish_payload = {
        "upload_phase": "finish",
        "video_id": video_id,
        "video_state": "PUBLISHED",
        "description": caption,
        "access_token": page_token,
    }

    finish_res = requests.post(init_url, data=finish_payload).json()
    return finish_res


def main():
    pages_json = os.environ.get("FB_PAGES_DATA")
    if not pages_json:
        raise ValueError(
            "Error: Secret 'FB_PAGES_DATA' tidak ditemukan atau kosong!"
        )

    pages = json.loads(pages_json)

    if not os.path.exists("videos.json"):
        raise FileNotFoundError("Error: File 'videos.json' tidak ditemukan!")

    with open("videos.json", "r", encoding="utf-8") as f:
        videos = json.load(f)

    updated = False
    for video in videos:
        # Mencari video pertama dengan status 'pending'
        if video.get("status") == "pending":
            video_url = video.get("url")
            title = video.get("title", "")
            description = video.get("description", "")

            caption = (
                f"{description}"
                if description
                else f"{title}\nhttps://part-selanjutnya.github.io/part-selanjutnya/\nTonton selanjutnya☝️"
            )

            print("==========================================")
            print(f"Memproses video: {title}")
            print(f"URL: {video_url}")
            print("==========================================")

            temp_file = "temp_video.mp4"
            try:
                # 1. Unduh dari Google Drive
                download_from_google_drive(video_url, temp_file)

                # 2. Unggah sebagai Reels ke seluruh halaman Facebook
                success_count = 0
                for page in pages:
                    page_name = page.get("name", "Halaman")
                    page_id = page.get("id") or page.get("page_id")
                    page_token = page.get("token") or page.get("access_token")

                    print(f"Mengunggah ke halaman: {page_name} ({page_id})...")

                    res = upload_reels_to_page(
                        page_id, page_token, temp_file, caption
                    )

                    if (
                        res.get("success")
                        or "x-fb-trace-id" in res
                        or "video_id" in res
                    ):
                        print(" -> Sukses terunggah sebagai Reels!")
                        success_count += 1
                    else:
                        print(f" -> Respon Upload: {json.dumps(res)}")

                if os.path.exists(temp_file):
                    os.remove(temp_file)

                if success_count > 0:
                    video["status"] = "completed"
                    updated = True
                    break
                else:
                    raise RuntimeError(
                        "Gagal mengunggah Reels ke halaman Facebook. Periksa token/izin halaman Anda."
                    )

            except Exception as e:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                raise RuntimeError(f"Gagal memproses video: {e}")

    # Simpan kembali status 'completed' ke videos.json
    if updated:
        with open("videos.json", "w", encoding="utf-8") as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)
        print("videos.json berhasil diperbarui menjadi 'completed'.")


if __name__ == "__main__":
    main()
