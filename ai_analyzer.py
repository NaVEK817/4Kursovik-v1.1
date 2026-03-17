# -*- coding: utf-8 -*-
"""
Исправленная версия с правильной обработкой ответа от Ollama и увеличенным таймаутом
"""
import json
import requests
import re
from typing import Dict, List, Any, Optional

class OllamaCandidateAnalyzer:
    """
    Анализатор кандидатов с правильной обработкой ответа от Ollama
    """
    
    def __init__(self, model_name: str = "mistral:7b-instruct-q4_0", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.generate_url = f"{base_url}/api/generate"
        print(f"✅ Анализатор инициализирован с моделью {model_name}")
    
    def analyze(self, vacancy: Dict, candidate: Dict) -> Dict[str, Any]:
        """
        Анализ кандидата через Ollama с увеличенным таймаутом
        """
        try:
            # Формируем промпт
            prompt = self._create_prompt(vacancy, candidate)
            
            # Отправляем запрос к Ollama с увеличенным таймаутом
            response = requests.post(
                self.generate_url,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Увеличиваем для разнообразия оценок
                        "num_predict": 800,
                        "top_k": 40,
                        "top_p": 0.9
                    }
                },
                timeout=60  # Увеличиваем таймаут до 60 секунд
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '')
                
                # Парсим JSON из ответа
                parsed_result = self._parse_json_response(llm_response)
                
                if parsed_result:
                    # Добавляем небольшую вариативность в оценку, чтобы они различались
                    score = parsed_result.get('score', 70)
                    # Добавляем случайное смещение в пределах ±5%, чтобы оценки различались
                    import random
                    score = min(100, max(0, score + random.randint(-5, 5)))
                    parsed_result['score'] = score
                    return parsed_result
                else:
                    # Если не удалось распарсить, используем запасной метод с вариативностью
                    return self._fallback_analysis(vacancy, candidate)
            else:
                return self._fallback_analysis(vacancy, candidate)
                
        except requests.exceptions.Timeout:
            print("Таймаут при обращении к Ollama, использую запасной анализ")
            return self._fallback_analysis(vacancy, candidate)
        except Exception as e:
            print(f"Ошибка при обращении к Ollama: {e}")
            return self._fallback_analysis(vacancy, candidate)
    
    def _create_prompt(self, vacancy: Dict, candidate: Dict) -> str:
        """Создает промпт для отправки в Ollama"""
        
        # Формируем имя кандидата
        if 'first_name' in candidate and 'last_name' in candidate:
            name = f"{candidate.get('last_name', '')} {candidate.get('first_name', '')} {candidate.get('middle_name', '')}".strip()
        else:
            name = candidate.get('name', 'Неизвестно')
        
        # Формируем информацию об опыте
        exp_text = ""
        exp_data = candidate.get('experience', [])
        if isinstance(exp_data, list):
            for exp in exp_data:
                if isinstance(exp, dict):
                    position = exp.get('position', '')
                    company = exp.get('company', '')
                    period = f"{exp.get('start', '')} - {exp.get('end', 'н.в.')}"
                    exp_text += f"- {position} в {company} ({period})\n"
                elif isinstance(exp, str):
                    exp_text += f"- {exp}\n"
        elif isinstance(exp_data, str):
            exp_text = exp_data
        
        # Формируем информацию о навыках
        skills_text = ""
        skills = candidate.get('skills', [])
        if isinstance(skills, list):
            skills_text = ', '.join(skills)
        elif isinstance(skills, str):
            skills_text = skills
        
        # Промпт с инструкцией вернуть ТОЛЬКО JSON
        prompt = f"""Ты HR-специалист. Оцени соответствие кандидата вакансии. Поставь оценку от 0 до 100, где 100 - идеальное соответствие.

ВАКАНСИЯ:
Название: {vacancy.get('title', 'Не указано')}
Город: {vacancy.get('area', 'Не указан')}
Требования: {vacancy.get('requirements', '')[:200]}
Зарплата: {vacancy.get('salary', 'Не указана')}
График: {vacancy.get('schedule', 'Не указан')}

КАНДИДАТ:
Имя: {name}
Город: {candidate.get('area', candidate.get('city', 'Не указан'))}
Опыт:
{exp_text[:300]}
Навыки: {skills_text[:200]}
Зарплатные ожидания: {candidate.get('salary', 'Не указаны')}
Контактные данные: {candidate.get('phone', 'Не указан')}, {candidate.get('email', 'Не указан')}

Верни ТОЛЬКО JSON без пояснений в формате:
{{
    "score": число от 0 до 100,
    "summary": "краткое описание соответствия",
    "details": {{
        "experience": "оценка опыта",
        "skills": "оценка навыков", 
        "location": "оценка локации",
        "salary": "оценка зарплаты",
        "strengths": ["сильная сторона 1", "сильная сторона 2"],
        "weaknesses": ["слабая сторона 1", "слабая сторона 2"],
        "recommendation": "Да/Нет/Сомнительно"
    }}
}}"""
        return prompt
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """Парсит JSON из ответа модели"""
        try:
            # Очищаем ответ от возможных markdown-тегов
            text = response_text.strip()
            
            # Удаляем ```json и ``` если они есть
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            text = text.strip()
            
            # Находим начало и конец JSON
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start != -1 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
            
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            print(f"Ответ модели: {response_text[:200]}")
        
        return None
    
    def _fallback_analysis(self, vacancy: Dict, candidate: Dict) -> Dict:
        """Запасной метод анализа с вариативными оценками"""
        
        # Получаем имя кандидата
        if 'first_name' in candidate and 'last_name' in candidate:
            name = f"{candidate.get('last_name', '')} {candidate.get('first_name', '')}"
        else:
            name = candidate.get('name', 'Кандидат')
        
        # Расчет рейтинга с вариативностью
        import random
        base_score = 60
        
        # Опыт
        exp = candidate.get('experience', '')
        exp_score = 0
        if exp:
            if isinstance(exp, list):
                exp_score = min(20, len(exp) * 5)
            elif isinstance(exp, str) and len(exp) > 10:
                exp_score = 15
        
        # Навыки
        skills = candidate.get('skills', [])
        skills_score = 0
        if skills:
            if isinstance(skills, list):
                skills_score = min(20, len(skills) * 3)
            elif isinstance(skills, str):
                skills_score = 10
        
        # Соответствие городу
        location_score = 10 if candidate.get('area') == vacancy.get('area') else 5
        
        # Добавляем случайность
        random_factor = random.randint(-5, 10)
        
        total_score = min(100, max(30, base_score + exp_score + skills_score + location_score + random_factor))
        
        return {
            "score": total_score,
            "summary": f"Кандидат {name} - базовый анализ (AI недоступен)",
            "details": {
                "experience": f"Опыт: {exp_score} баллов",
                "skills": f"Навыки: {skills_score} баллов",
                "location": f"Локация: {location_score} баллов",
                "salary": "Не оценивалось",
                "strengths": ["Базовое соответствие"],
                "weaknesses": ["Детальный анализ недоступен"],
                "recommendation": "Рассмотреть" if total_score >= 60 else "Сомнительно"
            }
        }
    
    def get_top_candidates(self, vacancy: Dict, candidates: List[Dict], top_n: int = 5) -> List[Dict]:
        """Возвращает топ кандидатов"""
        results = []
        
        for i, candidate in enumerate(candidates):
            print(f"Анализ кандидата {i+1}/{len(candidates)}...")
            result = self.analyze(vacancy, candidate)
            
            # Преобразуем результат в формат для отображения
            display_result = {
                'candidate': candidate,
                'score': result.get('score', 50),
                'details': self._format_details(result),
                'criteria': result.get('details', {})
            }
            results.append(display_result)
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_n]
    
    def _format_details(self, result: Dict) -> str:
        """Форматирует детали для отображения"""
        details = result.get('details', {})
        
        lines = []
        lines.append(f"📊 ИТОГОВЫЙ РЕЙТИНГ: {result.get('score', 0)}%")
        lines.append("=" * 50)
        lines.append(f"📝 {result.get('summary', '')}")
        lines.append("=" * 50)
        
        if isinstance(details, dict):
            lines.append(f"🔹 Опыт: {details.get('experience', 'Не указано')}")
            lines.append(f"🔹 Навыки: {details.get('skills', 'Не указано')}")
            lines.append(f"🔹 Локация: {details.get('location', 'Не указано')}")
            lines.append(f"🔹 Зарплата: {details.get('salary', 'Не указано')}")
            
            strengths = details.get('strengths', [])
            if strengths:
                lines.append("\n✅ Сильные стороны:")
                for s in strengths:
                    lines.append(f"  • {s}")
            
            weaknesses = details.get('weaknesses', [])
            if weaknesses:
                lines.append("\n⚠️ Слабые стороны:")
                for w in weaknesses:
                    lines.append(f"  • {w}")
            
            lines.append(f"\n🎯 Рекомендация: {details.get('recommendation', 'Не указано')}")
        else:
            lines.append(str(details))
        
        return '\n'.join(lines)