class GPTUtils:
    @staticmethod
    def row_to_generate_description_prompt(data: list) -> str:
        """
        Превращает несколько ячеек с данными в единый промпт для ChatGPT
        :param data:
        :return:
        """
        item_name, item_params, old_desc, keywords, request = data[4:9]
        item_params = "<не указано>" if not item_params else item_params
        old_desc = "<не указано>" if not old_desc else old_desc
        prompt = (
            f"{request}\n"
            f"Товар: {item_name}.\n"
            f"Характеристики: {item_params}.\n"
            f"Ключевые слова: {keywords}.\n"
            f"Старое описание: {old_desc}."
        )
        return prompt

    @staticmethod
    def check_keywords_in_desc_prompt(keywords: str, description: str) -> str:
        prompt = (f"Текст: {description}\n"
                  f"Ключевые слова: {keywords}\n"
                  f"Задача: Из готового описания отбери и напиши вошедшие ключевые слова,"
                  f" объедения по суффиксам, окончаниям и т.д."
                  f" ВЫВЕСТИ НАДО ТОЛЬКО СПИСОК КЛЮЧЕВЫХ СЛОВ БЕЗ ЛИШНЕЙ ИНФОРМАЦИИ")
        return prompt


class TextUtils:
    """
    Утилиты для работы с текстом
    """

    @staticmethod
    def transform_dict_keys_to_str(data: dict):
        return ", ".join([str(i) for i in list(data.keys())])
    @staticmethod
    def count_keywords(text: str, data: list) -> str:
        """
        **WIP**
        Проверяет вхождение ключевых слов в тексте
        :param text:
        :param data:
        :return: Возвращает ключевые слова, использованные в тексте
        """
        used_keywords = []
        keywords = data[3].split(",")
        for i in keywords:
            if i.lower() in text.lower():
                used_keywords.append(i)
        return ", ".join(used_keywords)