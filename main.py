import os
import sys

# ⚡ suppress tensorflow logs
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from config import DEFAULT_INPUT, DEFAULT_OUTPUT
from core.renamer import rename_file
from core.organiser import organize_file
from core.scanner import scan_files
from logs.logger import logger


def get_input_folder():
    # 👉 if user passes path
    if len(sys.argv) > 1:
        return sys.argv[1]

    # 👉 fallback
    return DEFAULT_INPUT


def main():
    input_folder = get_input_folder()
    output_folder = DEFAULT_OUTPUT

    logger.info(f"📂 Input Folder: {input_folder}")
    logger.info(f"📁 Output Folder: {output_folder}\n")

    if not os.path.exists(input_folder):
        logger.error("❌ Input folder does not exist!")
        return

    files = scan_files(input_folder)

    if not files:
        logger.warning("⚠️ No files found.")
        return

    for i, file_path in enumerate(files, start=1):
        try:
            logger.info(f"[{i}/{len(files)}] {file_path}")

            new_name = rename_file(file_path)

            if not new_name:
                continue

            organize_file(file_path, new_name, output_folder)

        except Exception as e:
            logger.error(f"❌ Error: {e}")

    logger.info("\n✅ Done!")


if __name__ == "__main__":
    main()