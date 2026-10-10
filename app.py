import time
from io import BytesIO

import streamlit as st
from google import genai
from huggingface_hub import InferenceClient


# -----------------------------
# Настройки страницы
# -----------------------------

st.set_page_config(
    page_title="SmartChef AI",
    page_icon="🍳",
    layout="wide"
)

st.title("🍳 SmartChef AI")
st.write(
    "Выберите продукты, укажите время приготовления "
    "и получите рецепт от искусственного интеллекта!"
)


# -----------------------------
# Подключение Gemini
# -----------------------------

try:
    gemini_client = genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )
except Exception:
    st.error(
        "Не удалось подключить Gemini. "
        "Проверьте API-ключ в настройках приложения."
    )
    st.stop()


# -----------------------------
# Данные приложения
# -----------------------------

if "last_recipe" not in st.session_state:
    st.session_state.last_recipe = ""

if "last_image" not in st.session_state:
    st.session_state.last_image = None

if "favorites" not in st.session_state:
    st.session_state.favorites = []


# -----------------------------
# Выбор продуктов
# -----------------------------

st.header("🥕 Что есть в холодильнике?")

available_ingredients = [
    "🥚 Яйца",
    "🥛 Молоко",
    "🧀 Сыр",
    "🍗 Курица",
    "🍝 Макароны",
    "🥔 Картофель",
    "🍅 Помидоры",
    "🥒 Огурцы",
    "🧅 Лук"
]

selected_ingredients = st.multiselect(
    "Выберите продукты:",
    available_ingredients
)

custom_ingredients = st.text_input(
    "Или добавьте свои продукты:",
    placeholder="Например: рис, морковь, грибы"
)

# Объединяем выбранные и введённые продукты
all_ingredients = selected_ingredients.copy()

if custom_ingredients.strip():
    extra_ingredients = [
        item.strip()
        for item in custom_ingredients.split(",")
        if item.strip()
    ]
    all_ingredients.extend(extra_ingredients)

# Убираем повторения
all_ingredients = list(dict.fromkeys(all_ingredients))


# -----------------------------
# Настройки блюда
# -----------------------------

st.header("⚙️ Настройки блюда")

cooking_time = st.slider(
    "Максимальное время приготовления (минуты):",
    min_value=10,
    max_value=120,
    value=30,
    step=5
)

dish_type = st.selectbox(
    "Какое блюдо приготовить?",
    [
        "Завтрак",
        "Обед",
        "Ужин",
        "Перекус"
    ]
)


# -----------------------------
# Генерация рецепта
# -----------------------------

if st.button("✨ Найти рецепт!", type="primary"):

    if not all_ingredients:
        st.warning(
            "Пожалуйста, выберите хотя бы один продукт!"
        )

    else:
        ingredients_text = ", ".join(all_ingredients)

        recipe_prompt = f"""
Ты профессиональный шеф-повар и помощник по приготовлению еды.

Придумай простой и реалистичный рецепт на русском языке.

Используй эти продукты:
{ingredients_text}

Тип блюда: {dish_type}
Максимальное время приготовления: {cooking_time} минут.

Требования:
- Используй выбранные продукты.
- Укажи дополнительные ингредиенты, если они необходимы.
- Уложись в указанное время приготовления.
- Укажи количество порций.
- Используй понятные инструкции.

Ответь в таком формате:

🍳 Название блюда

⏱️ Время приготовления:
Укажи время.

🥕 Ингредиенты:
- Ингредиент с количеством

👩‍🍳 Приготовление:
1. Первый шаг.
2. Второй шаг.
3. Третий шаг.

📊 Пищевая ценность на одну порцию:
- Калории: примерно ... ккал
- Белки: примерно ... г
- Жиры: примерно ... г
- Углеводы: примерно ... г

Пищевая ценность должна быть приблизительной.
Весь ответ напиши на русском языке.
"""

        with st.spinner(
            "🤖 Искусственный интеллект придумывает рецепт..."
        ):
            try:
                response = None

                for attempt in range(3):
                    try:
                        response = gemini_client.models.generate_content(
                            model="gemini-3.7-flash",
                            contents=recipe_prompt
                        )
                        break

                    except Exception:
                        if attempt == 2:
                            raise
                        time.sleep(2)

                if response and response.text:
                    st.session_state.last_recipe = response.text
                    st.session_state.last_image = None
                else:
                    st.error("Не удалось получить рецепт от ИИ.")

            except Exception as e:
                st.error(
                    "Не удалось создать рецепт. "
                    "Попробуйте ещё раз."
                )
                st.caption(str(e))


# -----------------------------
# Отображение рецепта
# -----------------------------

if st.session_state.last_recipe:

    st.divider()
    st.header("📝 Ваш рецепт")

    st.markdown(st.session_state.last_recipe)

    st.download_button(
        label="📥 Скачать рецепт",
        data=st.session_state.last_recipe,
        file_name="smartchef_recipe.txt",
        mime="text/plain"
    )

    # -------------------------
    # Генерация изображения
    # -------------------------

    st.divider()
    st.header("🖼️ Изображение блюда")

    if st.button("🎨 Сгенерировать изображение"):

        try:
            with st.spinner(
                "🎨 Искусственный интеллект создаёт изображение..."
            ):
                image_client = InferenceClient(
                    provider="auto",
                    api_key=st.secrets["HF_TOKEN"]
                )

                image_prompt = f"""
Create a realistic, high-quality food photograph
of the finished dish described below.

Dish:
{st.session_state.last_recipe}

Show the finished dish beautifully plated.
Use appetizing natural lighting and realistic food textures.
Clean background, professional food photography.
No text, no labels, no watermark.
"""

                image = image_client.text_to_image(
                    prompt=image_prompt,
                    model="black-forest-labs/FLUX.1-schnell"
                )

                image_buffer = BytesIO()
                image.save(image_buffer, format="PNG")

                st.session_state.last_image = (
                    image_buffer.getvalue()
                )

        except Exception as e:
            st.warning(
            "😔 Сейчас не удалось создать изображение. "
            "Генерация временно недоступна."
            )

    if st.session_state.last_image:
        st.image(
            st.session_state.last_image,
            caption="Изображение вашего блюда",
            use_container_width=True
        )

        st.download_button(
            label="📥 Скачать изображение",
            data=st.session_state.last_image,
            file_name="smartchef_dish.png",
            mime="image/png"
        )

    # -------------------------
    # Сохранение в избранное
    # -------------------------

    st.divider()

    if st.button("❤️ Добавить в избранное"):

        already_saved = any(
            item["recipe"] == st.session_state.last_recipe
            for item in st.session_state.favorites
        )

        if already_saved:
            st.info("Этот рецепт уже есть в избранном.")
        else:
            st.session_state.favorites.append({
                "recipe": st.session_state.last_recipe,
                "image": st.session_state.last_image
            })
            st.success("Рецепт добавлен в избранное!")


# -----------------------------
# Избранные рецепты
# -----------------------------

st.divider()
st.header("❤️ Избранные рецепты")

if not st.session_state.favorites:
    st.info(
        "Здесь будут отображаться рецепты, "
        "которые вы добавите в избранное."
    )

else:
    for index, favorite in enumerate(
        st.session_state.favorites
    ):

        with st.expander(f"🍽️ Рецепт №{index + 1}"):

            st.markdown(favorite["recipe"])

            if favorite["image"]:
                st.image(
                    favorite["image"],
                    caption="Изображение блюда",
                    use_container_width=True
                )

            st.download_button(
                label="📥 Скачать рецепт",
                data=favorite["recipe"],
                file_name=f"favorite_recipe_{index + 1}.txt",
                mime="text/plain",
                key=f"download_recipe_{index}"
            )

            if favorite["image"]:
                st.download_button(
                    label="📥 Скачать изображение",
                    data=favorite["image"],
                    file_name=f"favorite_image_{index + 1}.png",
                    mime="image/png",
                    key=f"download_image_{index}"
                )

            if st.button(
                "🗑️ Удалить из избранного",
                key=f"remove_favorite_{index}"
            ):
                st.session_state.favorites.pop(index)
                st.rerun()
