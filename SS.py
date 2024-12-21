import asyncio
import sys
from threading import Thread

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent
from playwright.async_api import async_playwright

liveID = "@noelwelldone" # p.m.names
client: TikTokLiveClient = TikTokLiveClient(unique_id=liveID)

# ตัวแปรสำหรับควบคุมลูป
loop_running = asyncio.Event()

keywords_responses = {
    "อันยองงับ": "สั่งขนมกดลิ้งที่หน้า bio ได้เลยค่ะ",
    # เพิ่มคำสำคัญอื่น ๆ ตามที่ต้องการ
}

# Define page and browser globally
browser = None
page = None


def check_for_keywords(comment: str) -> str:
    """Check if the comment contains any keywords."""
    for keyword, response in keywords_responses.items():
        if keyword in comment:
            return response
    return None


async def monitor_browser():
    """ตรวจสอบสถานะของเบราว์เซอร์"""
    try:
        while True:
            if not browser.is_connected():  # Check if browser is disconnected
                print("Browser is closed.")
                loop_running.clear()  # Stop the main loop
                break  # Exit the loop if browser is closed
            await asyncio.sleep(1)  # Check every 1 second
    except Exception as e:
        print(f"Error in monitor_browser: {e}")
    finally:
        print("Browser closed. Stopping the program...")
        loop_running.clear()  # Ensure the main loop is stopped when browser is closed


@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    """Handle connection event."""
    global browser, page
    print(f"Connected to @{event.unique_id} (Room ID: {client.room_id})")
    loop_running.set()  # เริ่มต้นลูปหลัก

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=False)
        context = await browser.new_context()  # ใช้ context ปกติ (ไม่ใช่ private)
        page = await context.new_page()  # เปิด page ใน context ปกติ
        await page.goto(f"https://www.tiktok.com/{liveID}/live")
        await page.wait_for_load_state("domcontentloaded")
        print("Page loaded successfully.")

        # เริ่มตรวจสอบสถานะเบราว์เซอร์
        asyncio.create_task(monitor_browser())

        # ลูปหลักจะรันต่อไปจนกว่า loop_running จะถูกเคลียร์
        while loop_running.is_set():
            await asyncio.sleep(1)  # รอ 1 วินาทีในแต่ละรอบ

    print("Program terminated.")  # แจ้งเตือนเมื่อโปรแกรมหยุดทำงาน


@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    """Handle comment events."""
    global page  # Ensure page is accessible here

    # แสดงคอมเมนต์ใน QTextEdit
    comment_text = f"{event.user.nickname} -> {event.comment}"
    window.comment_input.append(comment_text)  # เพิ่มข้อความใน QTextEdit

    response = check_for_keywords(event.comment)
    if response:
        try:
            # รอให้ element contenteditable ปรากฏใน DOM
            await page.wait_for_selector('.css-1l5p0r-DivEditor.e1ciaho81', timeout=10000)  # รอ 10 วินาที

            # ค้นหาช่องที่เป็น contenteditable โดยใช้ CSS selector
            editable_div = page.locator('.css-1l5p0r-DivEditor.e1ciaho81')

            # เติมข้อความลงใน div
            await editable_div.fill("อันยอง")  # เติมข้อความ "อันยอง" ลงใน div
            print("อันยองง")

            # ถ้าต้องการกด Enter หลังจากนั้น
            await editable_div.press("Enter")
            print(f"Bot responded: {response}")
        except Exception as e:
            print(f"Error while responding to comment: {e}")




class TikTokBotApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TikTok Live Bot")
        self.setGeometry(100, 100, 600, 400)

        self.layout = QVBoxLayout()

        self.output_label = QLabel("กำลังเชื่อมต่อ...", self)
        self.layout.addWidget(self.output_label)

        self.comment_input = QTextEdit(self)
        self.comment_input.setPlaceholderText("ใส่คอมเมนต์...")
        self.layout.addWidget(self.comment_input)

        self.response_button = QPushButton("ตอบกลับ", self)
        self.response_button.clicked.connect(self.on_button_press)
        self.layout.addWidget(self.response_button)

        self.setLayout(self.layout)

    def on_button_press(self):
        comment = self.comment_input.toPlainText()
        response = check_for_keywords(comment)
        if response:
            self.output_label.setText(f"Bot responded: {response}")
        else:
            self.output_label.setText("ไม่มีคำตอบสำหรับคำนี้")


def run_tiktok_client():
    try:
        client.run()
    except KeyboardInterrupt:
        print("Program stopped by user.")
        sys.exit(0)


if __name__ == '__main__':
    # Create an instance of the application
    app = QApplication(sys.argv)

    # Create the TikTokBotApp window
    window = TikTokBotApp()
    window.show()

    # Run TikTok client in a separate thread to prevent blocking the GUI
    tiktok_thread = Thread(target=run_tiktok_client, daemon=True)
    tiktok_thread.start()

    # Start the PyQt event loop
    sys.exit(app.exec_())
