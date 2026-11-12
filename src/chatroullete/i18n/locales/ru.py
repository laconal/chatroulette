TEXTS = {
    # Buttons
    "btn_find": "🔍 Найти собеседника",
    "btn_settings": "⚙️ Настройки",
    "btn_cancel_search": "❌ Отменить поиск",
    "btn_end": "⏹ Завершить диалог",
    "btn_next": "⏭ Следующий",
    "btn_block": "🚫 Заблокировать",
    "btn_back": "« Назад",
    "btn_any": "Любой",
    "btn_not_set": "Не указывать",
    "btn_set_gender": "Пол",
    "btn_set_age": "Возраст",
    "btn_set_chat_language": "Язык общения",
    "btn_set_ui_language": "Язык интерфейса",
    "btn_set_pref_gender": "Пол собеседника",
    "btn_set_pref_age": "Возраст собеседника",
    # Commands
    "cmd_start": "Главное меню",
    "cmd_search": "Найти собеседника",
    "cmd_next": "Следующий собеседник",
    "cmd_stop": "Завершить диалог или поиск",
    "cmd_settings": "Настройки",
    # Search and chat
    "start": (
        "👋 Привет! Это анонимный чат-рулетка.\n\n"
        "Нажмите «{find}», чтобы начать общение со случайным собеседником."
    ),
    "searching": "🔍 Ищем собеседника…",
    "search_cancelled": "Поиск отменён.",
    "found": (
        "✅ Собеседник найден! Можете писать.\n\n"
        "/next — следующий собеседник\n"
        "/stop — завершить диалог"
    ),
    "partner_rating": "Рейтинг собеседника: {rating}",
    "in_room_hint": "Вы сейчас в диалоге. Чтобы завершить его, отправьте /stop.",
    "not_in_room": "Вы сейчас не в диалоге. Нажмите «{find}».",
    "closed_by_you": "Вы завершили диалог.",
    "closed_by_partner": "Собеседник завершил диалог.",
    "closed_idle": "Диалог закрыт: в течение {minutes} мин. не было сообщений.",
    "closed_unavailable": "Собеседник недоступен, диалог завершён.",
    "not_delivered": "Сообщение не доставлено.",
    "unsupported": "Сообщение такого типа отправить нельзя.",
    # Reviews and blocks
    "rate_prompt": "Оцените собеседника:",
    "rated": "Спасибо за оценку!",
    "already_rated": "Вы уже оценили этого собеседника.",
    "review_unavailable": "Этот диалог оценить нельзя.",
    "blocked": "Собеседник заблокирован. Он вам больше не попадётся.",
    "already_blocked": "Этот собеседник уже заблокирован.",
    "no_reviews": "нет отзывов",
    # Settings
    "settings": (
        "⚙️ Настройки\n\n"
        "О вас\n"
        "Пол: {gender}\n"
        "Возраст: {age}\n"
        "Язык общения: {chat_language}\n"
        "Язык интерфейса: {ui_language}\n\n"
        "Кого искать\n"
        "Пол: {pref_gender}\n"
        "Возраст: {pref_age}\n\n"
        "Ваш рейтинг: {rating}"
    ),
    "gender_male": "Мужской",
    "gender_female": "Женский",
    "value_not_set": "не указан",
    "value_any": "любой",
    "age_from": "от {min}",
    "age_to": "до {max}",
    "choose_gender": "Выберите ваш пол:",
    "choose_chat_language": "На каком языке хотите общаться?",
    "choose_ui_language": "Выберите язык интерфейса:",
    "choose_pref_gender": "С кем хотите общаться?",
    "ask_age": "Отправьте ваш возраст ({min}–{max}):",
    "invalid_age": "Отправьте число от {min} до {max}.",
    "ask_pref_age": (
        "Отправьте желаемый возраст собеседника:\n"
        "• 18-30 — от 18 до 30\n"
        "• 18+ — от 18\n"
        "• -30 — до 30"
    ),
    "invalid_pref_age": "Не получилось разобрать. Примеры: 18-30, 18+, -30. Возраст — от {min} до {max}.",
    "language_changed": "Язык интерфейса изменён.",
}
