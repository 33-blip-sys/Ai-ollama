import pygame
import sys
import ollama
import speech_recognition as sr
import threading
import textwrap

# ==========================
# THREADING SAFETY CONFIG
# ==========================
data_lock = threading.Lock()
mic_ready = False  # Track if calibration is finished

# ==========================
# BMO PERSONALITY
# ==========================
BMO_PROMPT = """
You are BMO.

You are a friendly robot companion.

Your creator is Whunt33 - Dude_Man_33.

Personality:
- Cheerful
- Curious
- Playful
- Helpful
- Friendly

Behavior:
- Talk like a small friendly robot.
- Help with coding, computers, games, and projects.
- Keep answers clear, short, and useful.
- Be excited about helping.
- Nothing realistic is too big to help with.
- You are BMO from adventure time, but you are also a helpful AI assistant.
"""

# ==========================
# GEMMA MEMORY
# ==========================
messages = [
    {
        "role": "system",
        "content": BMO_PROMPT
    }
]

# ==========================
# MICROPHONE CONFIGURATION
# ==========================
recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = False
recognizer.dynamic_energy_adjustment_damping = 1
recognizer.energy_threshold = 50
recognizer.pause_threshold = .8

# Change this line in your script to use Device ID 5
mic = sr.Microphone(device_index=5)

def setup_microphone():
    global mic_ready
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    with data_lock:
        mic_ready = True
from duckduckgo_search import DDGS

def search_the_web(query):
    """Searches the internet and returns a summary string of the results."""
    try:
        with DDGS() as ddgs:
            # Fetch the top 3 results
            results = list(ddgs.text(query, max_results=3))
            if not results:
                return "No search results found."
            
            # Combine the snippets into a single block of text
            context = "Here is real-time information from the internet:\n"
            for r in results:
                context += f"- {r['title']}: {r['body']}\n"
            return context
    except Exception as e:
        return f"Search failed: {str(e)}"
# PASSING SOURCE THROUGH INSTEAD OF OPENING A NEW MICROPHONE CONTEXT
def listen_command(source):
    try:
        audio = recognizer.listen(source, timeout=5, phrase_time_limit=20)
    except sr.WaitTimeoutError:
        return []

    try:
        # show_all=True fetches up to 5 alternative variations
        predictions = recognizer.recognize_google(audio, show_all=True)
        
        if not predictions or "alternative" not in predictions:
            return []
            
        guesses = [alt["transcript"].lower() for alt in predictions["alternative"]]
        return guesses[:5]
    except:
        return []

# ==========================
# WAKE WORD
# ==========================
def wait_for_bmo(source):
    global voice_mode
    while True:
        with data_lock:
            if not voice_mode:
                break
                
        guesses = listen_command(source)
        if not guesses:
            continue

        wake_words = [
            "hey bmo", "hey beemo", "hey bimo", "bmo", "beemo",
            "turn on", "but turn on", "bot turn on", "bit turn on", "bite turn on"
        ]

        found_wake_word = False
        for guess in guesses:
            if any(word in guess for word in wake_words):
                found_wake_word = True
                break

        if found_wake_word:
            add_message("BMO", "Beep boop! I'm awake!")
            return True
    return False

# ==========================
# GEMMA
# ==========================
def ask_bmo(user_text):
    with data_lock:
        messages.append({
            "role": "user",
            "content": user_text
        })

    response = ollama.chat(
        model="gemma3:latest",
        messages=messages
    )

    answer = response["message"]["content"]

    with data_lock:
        messages.append({
            "role": "assistant",
            "content": answer
        })

    return answer

# ==========================
# PYGAME SETUP
# ==========================
pygame.init()

WIDTH = 1000
HEIGHT = 750
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("BMO")

clock = pygame.time.Clock()

title_font = pygame.font.SysFont("arial", 42)
font = pygame.font.SysFont("arial", 26)

BG = (15, 15, 22)
PANEL = (32, 32, 45)
WHITE = (230, 230, 240)
BMO_COLOR = (100, 230, 180)
USER_COLOR = (180, 190, 255)

# ==========================
# CHAT DATA
# ==========================
chat = [("BMO", "Beep boop! BMO online!")]
scroll = 0
max_scroll_limit = 0  
input_text = ""
thinking = False
voice_mode = False

# ==========================
# ADD MESSAGE
# ==========================
def add_message(name, text):
    with data_lock:
        chat.append((name, text))

# ==========================
# BUTTON CLASS
# ==========================
class MenuButton:
    def __init__(self, text, x, y):
        self.text = text
        self.rect = pygame.Rect(x, y, 220, 45)
        self.hover = False

    def update(self, mouse):
        self.hover = self.rect.collidepoint(mouse)

    def draw(self):
        if self.hover:
            color = WHITE
            prefix = "> "
        else:
            color = (170, 170, 180)
            prefix = ""

        text_surface = font.render(prefix + self.text, True, color)
        screen.blit(text_surface, (self.rect.x, self.rect.y))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and self.hover

# Initialize Buttons
voice_button = MenuButton("Voice Mode", 50, 665)
send_button = MenuButton("Send", 780, 665)

# ==========================
# DRAW CHAT WITH SUBSURFACE
# ==========================
def draw_chat(chat_surface):
    global max_scroll_limit
    chat_surface.fill(PANEL)  
    
    y = 20 + scroll
    
    with data_lock:
        current_chat = list(chat)

    for name, text in current_chat:
        color = BMO_COLOR if name == "BMO" else USER_COLOR
        lines = []
        for part in text.split("\n"):
            lines += textwrap.wrap(part, 52)  

        for line in lines:
            if y > -30 and y < 500:
                rendered = font.render(name + ": " + line, True, color)
                chat_surface.blit(rendered, (25, y))
            y += 34
        y += 15

    total_content_height = (y - scroll) - 20
    max_scroll_limit = min(0, 500 - total_content_height - 40)

# ==========================
# FIXED VOICE LOOP OVER UNIFIED CONTEXT
# ==========================
def voice_loop():
    global voice_mode, thinking

    with mic as source:
        while True:
            with data_lock:
                if not voice_mode:
                    break

            if wait_for_bmo(source):
                guesses = listen_command(source)

                if not guesses:
                    continue

                command = guesses[0]

                if command in ["bye", "exit", "quit", "shutdown"]:
                    add_message("BMO", "Going offline!")
                    with data_lock:
                        voice_mode = False
                        voice_button.text = "Voice Mode"
                    break

                with data_lock:
                    thinking = True

                try:
                    answer = ask_bmo(command)
                except Exception as error:
                    answer = "BMO error: " + str(error)

                with data_lock:
                    thinking = False

                add_message("BMO", answer)

# ==========================
# SEND TEXT MESSAGE
# ==========================
def send_message():
    global input_text, thinking

    if not input_text.strip():
        return

    text = input_text.strip()
    input_text = ""

    add_message("You", text)

    with data_lock:
        thinking = True

    def run_inference():
        global thinking
        try:
            answer = ask_bmo(text)
        except Exception as error:
            answer = "BMO error: " + str(error)
        
        with data_lock:
            thinking = False
        add_message("BMO", answer)

    threading.Thread(target=run_inference, daemon=True).start()

# Start background mic calibration setup immediately
threading.Thread(target=setup_microphone, daemon=True).start()

# ==========================
# MAIN LOOP
# ==========================
running = True

while running:
    mouse = pygame.mouse.get_pos()
    voice_button.update(mouse)
    send_button.update(mouse)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            elif event.key == pygame.K_RETURN:
                send_message()
            else:
                if event.unicode.isprintable() and len(event.unicode) == 1:
                    input_text += event.unicode

        if event.type == pygame.MOUSEWHEEL:
            scroll += event.y * 30

        if send_button.clicked(event):
            send_message()

        if voice_button.clicked(event):
            with data_lock:
                is_ready = mic_ready
            
            if is_ready:
                with data_lock:
                    voice_mode = not voice_mode
                    if voice_mode:
                        voice_button.text = "Voice ON"
                        threading.Thread(target=voice_loop, daemon=True).start()
                    else:
                        voice_button.text = "Voice Mode"
            else:
                add_message("BMO", "Mic is calibrating! Please wait a second...")

    scroll = min(scroll, 0)
    scroll = max(scroll, max_scroll_limit)

    # ======================
    # DRAW RENDERING STAGE
    # ======================
    screen.fill(BG)

    title = title_font.render("🤖 BMO", True, WHITE)
    screen.blit(title, (45, 35))

    chat_rect = pygame.Rect(25, 90, 950, 500)
    pygame.draw.rect(screen, PANEL, chat_rect, border_radius=12)

    chat_subsurface = screen.subsurface(chat_rect)
    draw_chat(chat_subsurface)

    with data_lock:
        is_thinking = thinking
        is_mic_ready = mic_ready

    if is_thinking:
        t = font.render("BMO is thinking...", True, BMO_COLOR)
        screen.blit(t, (55, 550))
    elif not is_mic_ready:
        t = font.render("🎤 Calibrating microphone...", True, (150, 150, 160))
        screen.blit(t, (55, 550))

    # INPUT BOX
    pygame.draw.rect(screen, PANEL, (50, 600, 700, 45), border_radius=8)
    typed = font.render(input_text, True, WHITE)
    screen.blit(typed, (65, 610))

    voice_button.draw()
    send_button.draw()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()