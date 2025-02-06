import os
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from io import BytesIO
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
STABILITY_API_KEY = "sk-zf1QxlGZYFWggRLzC0pl5fiKHX36AqJoZcKDELePZr08yelT"
LLM_MODEL = "gpt-4o-mini"

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Function to generate story using OpenAI
def generate_story(prompt):
    if not prompt.strip():
        st.error("Error: Prompt cannot be empty for story generation.")
        return ""

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error generating story: {e}")
        return ""

# Function to generate image using Stability AI
def generate_image_stability(prompt):
    if not prompt.strip():
        st.error("Error: Prompt cannot be empty for image generation.")
        return None

    try:
        url = "https://api.stability.ai/v2beta/stable-image/generate/core"
        headers = {
            "Authorization": f"Bearer {STABILITY_API_KEY}",
            "Accept": "image/*"
        }
        files = {
            'prompt': (None, prompt),
            'output_format': (None, 'png'),
            'aspect_ratio': (None, '1:1')
        }

        response = requests.post(url, headers=headers, files=files)

        if response.status_code == 200:
            return response.content  
        else:
            st.error(f"Stability AI: Bad Request. Response: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Stability AI Error: {e}")
        return None

# Function to generate image using OpenAI DALL-E (Fallback)
def generate_image_dalle(prompt):
    if not prompt.strip():
        return None

    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1
        )
        return response.data[0]['url']
    except Exception as e:
        st.error(f"DALL-E Error: {e}")
        return None

# Function to wrap text within a given width
def wrap_text(text, font, width):
    draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))  
    lines = []
    words = text.split()
    line = ""

    for word in words:
        test_line = f"{line} {word}".strip()
        text_width = draw.textbbox((0, 0), test_line, font=font)[2]  
        
        if text_width <= width:
            line = test_line
        else:
            lines.append(line)
            line = word

    if line:
        lines.append(line)

    return "\n".join(lines)

# Function to create comic panel with image, speech bubble, and text
def create_comic_panel(image_data, text):
    if image_data is None:
        return None

    try:
        if isinstance(image_data, bytes):
            img = Image.open(BytesIO(image_data))
        else:
            img = Image.open(requests.get(image_data, stream=True).raw)

        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)  

        draw = ImageDraw.Draw(img)

        border_padding = 10
        width, height = img.size
        draw.rectangle([border_padding, border_padding, width-border_padding, height-border_padding], outline="black", width=5)

        
        bubble_padding = 20
        bubble_margin = 10
        bubble_width = width - bubble_margin * 2
        bubble_height = 100  
        bubble_position = (bubble_margin, height - bubble_height - bubble_padding)

        draw.rounded_rectangle(
            [bubble_position, (bubble_margin + bubble_width, bubble_position[1] + bubble_height)],
            radius=20, outline="black", width=4, fill="white"
        )

        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except IOError:
            font = ImageFont.load_default()

        wrapped_text = wrap_text(text, font, bubble_width - bubble_margin * 2)
        draw.text((bubble_position[0] + bubble_margin, bubble_position[1] + bubble_margin), wrapped_text, fill="black", font=font)

        return img
    except Exception as e:
        st.error(f"Error creating comic panel: {e}")
        return None

# Function to generate comic panels
def generate_comic_panels(story_parts):
    panels = []
    for part in story_parts:
        if not part:
            continue
        image_data = generate_image_stability(part)
        if not image_data:
            st.warning("Falling back to DALL-E for image generation.")
            image_data = generate_image_dalle(part)
        if image_data:
            panel = create_comic_panel(image_data, part)
            if panel:
                panels.append(panel)
            else:
                st.error(f"Failed to create panel for: {part}")
        else:
            st.error(f"Failed to generate image for: {part}")
    return panels

# Function to split story into parts
def split_story_into_parts(story, max_parts=4):
    sentences = [s.strip() for s in story.split(".") if s.strip()]
    return sentences[:max_parts] if sentences else []

# Streamlit Web App UI
st.set_page_config(page_title="ComicCrafter AI", page_icon="🎨", layout="wide")
st.title("📖 ComicCrafter AI 🎨")
st.markdown("### Transform your creative ideas into visual stories!")

# Sidebar for user input
with st.sidebar:
    st.header("✨ Get Started")
    prompt = st.text_input("Enter your comic idea:", placeholder="A superhero cat saves the city...")
    st.markdown("---")
    st.subheader("About ComicCrafter")
    st.write(
        "ComicCrafter AI uses advanced AI models to generate engaging comic stories and visual panels. "
        "Simply input your idea, and let AI do the rest!"
    )
    st.markdown("---")
    st.write("Made with ❤️ by Himanshu")

if st.button("Generate Comic"):
    if prompt.strip():
        with st.spinner("Generating story..."):
            story = generate_story(prompt)

        if story:
            story_parts = split_story_into_parts(story)
            if story_parts:
                with st.spinner("Generating comic panels..."):
                    panels = generate_comic_panels(story_parts)

                if panels:
                    st.markdown("### Your Comic Panels")
                    for idx, panel in enumerate(panels):
                        st.image(panel, caption=f"Panel {idx + 1}")
                else:
                    st.error("Failed to generate any comic panels.")
            else:
                st.error("Story generation produced no meaningful parts.")
        else:
            st.error("Failed to generate story. Please try again.")
    else:
        st.warning("Please enter a valid comic idea.")
