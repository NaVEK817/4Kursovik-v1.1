# -*- coding: utf-8 -*-
"""
Главное окно приложения с таблицей вакансий и контекстным меню
"""
import json
import os
from datetime import datetime
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QPushButton, QLabel, QMessageBox, QMenu,
                             QDialog, QTextEdit, QVBoxLayout as QVBoxDialog,
                             QInputDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QCursor, QColor
import styles

# Файл для хранения статусов анализа
ANALYSIS_STATUS_FILE = "analysis_status.json"

# Импорты для новых окон
from ai_schedule_manager import AIScheduleManager
from messages_window import MessagesWindow


class VacancyDetailDialog(QDialog):
    """Диалог с полной информацией о вакансии"""

    def __init__(self, vacancy, parent=None):
        super().__init__(parent)
        self.vacancy = vacancy
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Детали вакансии: {self.vacancy.get('title', '')}")
        self.setGeometry(300, 300, 700, 600)
        self.setStyleSheet(styles.MAIN_STYLE)

        layout = QVBoxDialog()
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        title_label = QLabel(self.vacancy.get('title', ''))
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {styles.S7_GREEN};")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        # Основная информация
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setStyleSheet(f"background-color: {styles.S7_WHITE};")

        # Формирование текста
        info = f"""
        <table width="100%" cellpadding="5">
            <tr><td width="150"><b>ID:</b></td><td>{self.vacancy.get('id', '')}</td></tr>
            <tr><td><b>Название:</b></td><td>{self.vacancy.get('title', '')}</td></tr>
            <tr><td><b>Зарплата:</b></td><td>{self.vacancy.get('salary', 'Не указана')}</td></tr>
            <tr><td><b>Город:</b></td><td>{self.vacancy.get('area', '')}</td></tr>
            <tr><td><b>Опыт:</b></td><td>{self.vacancy.get('experience', '')}</td></tr>
            <tr><td><b>График:</b></td><td>{self.vacancy.get('schedule', '')}</td></tr>
            <tr><td><b>Занятость:</b></td><td>{self.vacancy.get('employment', '')}</td></tr>
            <tr><td><b>Дата публикации:</b></td><td>{self.vacancy.get('published_at', '')}</td></tr>
        </table>

        <h3 style='color: {styles.S7_GREEN}; margin-top: 20px;'>Требования</h3>
        <p>{self.vacancy.get('requirements', 'Не указаны')}</p>

        <h3 style='color: {styles.S7_GREEN};'>Обязанности</h3>
        <p>{self.vacancy.get('responsibilities', 'Не указаны')}</p>

        <h3 style='color: {styles.S7_GREEN};'>Условия</h3>
        <p>{self.vacancy.get('conditions', 'Не указаны')}</p>

        <h3 style='color: {styles.S7_GREEN};'>Ключевые навыки</h3>
        <p>{self.vacancy.get('skills', 'Не указаны')}</p>

        <h3 style='color: {styles.S7_GREEN};'>Ссылка</h3>
        <p><a href="{self.vacancy.get('link', '#')}">{self.vacancy.get('link', '')}</a></p>
        """

        info_text.setHtml(info)
        layout.addWidget(info_text)

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        close_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.vacancies = []
        self.schedule_manager = AIScheduleManager()
        self.analysis_status = self.load_analysis_status()  # Загружаем статусы
        self.init_ui()
        self.load_vacancies()

    def load_analysis_status(self):
        """Загружает статусы анализа из файла"""
        if os.path.exists(ANALYSIS_STATUS_FILE):
            try:
                with open(ANALYSIS_STATUS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_analysis_status(self):
        """Сохраняет статусы анализа в файл"""
        try:
            with open(ANALYSIS_STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения статусов: {e}")

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle(f"S7 Recruitment - Главная (Пользователь: {self.user_data.get('username', '')})")
        self.setGeometry(100, 100, 1400, 800)
        self.setStyleSheet(styles.MAIN_STYLE)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Верхняя панель с кнопками навигации
        nav_layout = QHBoxLayout()

        # Кнопки навигации
        self.schedule_btn = QPushButton("📅 Расписание собеседований")
        self.schedule_btn.clicked.connect(self.open_schedule_window)
        nav_layout.addWidget(self.schedule_btn)

        self.messages_btn = QPushButton("📬 Сообщения")
        self.messages_btn.clicked.connect(self.open_messages_window)
        self.messages_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.S7_LIGHT_GREEN};
            }}
        """)
        nav_layout.addWidget(self.messages_btn)

        self.stats_btn = QPushButton("📊 Статистика")
        self.stats_btn.clicked.connect(self.show_schedule_stats)
        nav_layout.addWidget(self.stats_btn)

        self.update_btn = QPushButton("🔄 Обновление данных")
        self.update_btn.clicked.connect(self.open_update_window)
        nav_layout.addWidget(self.update_btn)

        # Кнопка управления пользователями (только для админа)
        if self.user_data.get('role') == 'admin':
            self.users_btn = QPushButton("👥 Управление пользователями")
            self.users_btn.clicked.connect(self.open_users_window)
            nav_layout.addWidget(self.users_btn)

        nav_layout.addStretch()

        # Информация о пользователе
        user_label = QLabel(f"👤 {self.user_data.get('username', '')} ({self.user_data.get('role', '')})")
        user_label.setStyleSheet(f"color: {styles.S7_GREEN}; font-weight: bold;")
        nav_layout.addWidget(user_label)

        main_layout.addLayout(nav_layout)

        # Заголовок таблицы
        header_label = QLabel("Актуальные вакансии")
        header_label.setObjectName("headerLabel")
        main_layout.addWidget(header_label)

        # Таблица вакансий
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        # Включение контекстного меню
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # Установка колонок
        columns = ["ID", "Название", "Зарплата", "Город", "Опыт", "График",
                   "Занятость", "Дата публикации", "Навыки", "Статус анализа"]
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)

        # Растягивание колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Название
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Зарплата
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Город
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Опыт
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # График
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Занятость
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Дата
        header.setSectionResizeMode(8, QHeaderView.Stretch)  # Навыки
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Статус анализа

        main_layout.addWidget(self.table)

        # Нижняя панель с информацией
        bottom_layout = QHBoxLayout()

        self.count_label = QLabel("Загрузка вакансий...")
        bottom_layout.addWidget(self.count_label)

        bottom_layout.addStretch()

        refresh_btn = QPushButton("🔄 Обновить таблицу")
        refresh_btn.clicked.connect(self.load_vacancies)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        bottom_layout.addWidget(refresh_btn)

        main_layout.addLayout(bottom_layout)

    # === МЕТОДЫ ДЛЯ ОТКРЫТИЯ ОКОН ===

    def open_schedule_window(self):
        """Открытие окна расписания собеседований"""
        try:
            from schedule_window import ScheduleWindow
            self.schedule_window = ScheduleWindow(self.user_data)
            self.schedule_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть расписание: {str(e)}")

    def open_messages_window(self):
        """Открывает окно сообщений"""
        try:
            self.messages_window = MessagesWindow(self.user_data, self.schedule_manager)
            self.messages_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть окно сообщений: {str(e)}")

    def show_schedule_stats(self):
        """Показывает статистику расписания"""
        try:
            stats = self.schedule_manager.get_schedule_statistics()

            # Формируем текст статистики
            text = f"""
📊 ОБЩАЯ СТАТИСТИКА РАСПИСАНИЯ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 Всего собеседований: {stats.get('total_interviews', 0)}
📅 Дней с собеседованиями: {stats.get('days_with_interviews', 0)}
📊 В среднем в день: {stats.get('average_per_day', 0):.1f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 СТАТУСЫ СОБЕСЕДОВАНИЙ:
• Запланировано: {stats.get('status_stats', {}).get('scheduled', 0)}
• Перенесено: {stats.get('status_stats', {}).get('rescheduled', 0)}
• Завершено: {stats.get('status_stats', {}).get('completed', 0)}
• Отменено: {stats.get('status_stats', {}).get('cancelled', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📬 СООБЩЕНИЯ:
• Всего: {stats.get('message_stats', {}).get('total', 0)}
• Непрочитанных: {stats.get('message_stats', {}).get('unread', 0)}
• Ожидают ответа: {stats.get('message_stats', {}).get('pending_requests', 0)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 САМЫЕ ЗАГРУЖЕННЫЕ ДНИ:
"""
            for date, count in stats.get('busiest_days', []):
                text += f"  • {date}: {count} собеседований\n"

            # Предстоящие собеседования
            upcoming = stats.get('upcoming_interviews', [])
            if upcoming:
                text += f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📅 БЛИЖАЙШИЕ:\n"
                for i in upcoming[:3]:
                    text += f"  • {i.get('date')} {i.get('time')}: {i.get('candidate')}\n"

            QMessageBox.information(self, "Статистика расписания", text)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить статистику: {str(e)}")

    def open_update_window(self):
        """Открытие окна обновления данных"""
        try:
            from update_window import UpdateWindow
            self.update_window = UpdateWindow()
            self.update_window.show()
            self.update_window.update_completed.connect(self.load_vacancies)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть окно обновления: {str(e)}")

    def open_users_window(self):
        """Открытие окна управления пользователями"""
        try:
            from users_window import UsersWindow
            self.users_window = UsersWindow(self.user_data.get('role'))
            self.users_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть окно пользователей: {str(e)}")

    # === МЕТОДЫ ДЛЯ РАБОТЫ С ВАКАНСИЯМИ ===

    def show_context_menu(self, pos):
        """Показать контекстное меню при правом клике"""
        row = self.table.currentRow()
        if row >= 0:
            vacancy = self.vacancies[row]
            vacancy_id = str(vacancy.get('id', ''))
            
            menu = QMenu()

            view_action = menu.addAction("👁️ Просмотреть детали")
            view_action.triggered.connect(self.show_vacancy_details)

            menu.addSeparator()

            ai_action = menu.addAction("🤖 Запустить анализ кандидатов")
            ai_action.triggered.connect(self.analyze_candidates_for_vacancy)

            # Если анализ завершен, показываем кнопку загрузки из кэша
            if self.analysis_status.get(vacancy_id) == 'completed':
                cache_action = menu.addAction("💾 Загрузить результаты из кэша")
                cache_action.triggered.connect(self.load_from_cache)

            # Если анализ прерван
            if self.analysis_status.get(vacancy_id) == 'interrupted':
                status_action = menu.addAction("⚠️ Анализ был прерван (запустите заново)")
                status_action.setEnabled(False)

            # Если анализ в процессе
            if self.analysis_status.get(vacancy_id) == 'in_progress':
                status_action = menu.addAction("⏳ Анализ в процессе...")
                status_action.setEnabled(False)

            # Если анализ завершен, добавляем пункты создания оффера
            if self.analysis_status.get(vacancy_id) == 'completed':
                menu.addSeparator()
                
                # Для лучшего кандидата
                best_offer_action = menu.addAction("🏆 Создать оффер для лучшего кандидата")
                best_offer_action.triggered.connect(lambda: self.create_offer_for_best_candidate(vacancy))
                
                # Для кандидата по выбору
                select_offer_action = menu.addAction("📋 Выбрать кандидата из топа")
                select_offer_action.triggered.connect(lambda: self.create_offer_for_selected_candidate(vacancy))

            menu.exec_(QCursor.pos())

    def show_vacancy_details(self):
        """Показать детали выбранной вакансии"""
        row = self.table.currentRow()
        if row >= 0:
            vacancy = self.vacancies[row]
            dialog = VacancyDetailDialog(vacancy, self)
            dialog.exec_()

    def analyze_candidates_for_vacancy(self):
        """Открыть окно анализа кандидатов для выбранной вакансии"""
        row = self.table.currentRow()
        if row >= 0:
            try:
                from ai_agent_window import AIAgentWindow
                vacancy = self.vacancies[row]
                vacancy_id = str(vacancy.get('id', ''))
                
                # Устанавливаем статус "в процессе"
                self.analysis_status[vacancy_id] = 'in_progress'
                self.save_analysis_status()
                self.update_table()
                
                self.ai_window = AIAgentWindow(vacancy)
                
                # Подключаем сигналы для обновления статуса
                self.ai_window.analysis_completed.connect(lambda: self.mark_vacancy_analyzed(vacancy_id, 'completed'))
                self.ai_window.analysis_interrupted.connect(lambda: self.mark_vacancy_analyzed(vacancy_id, 'interrupted'))
                self.ai_window.destroyed.connect(lambda: self.check_analysis_status(vacancy_id))
                
                self.ai_window.show()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть анализ: {str(e)}")
                # В случае ошибки сбрасываем статус
                vacancy_id = str(self.vacancies[row].get('id', ''))
                self.analysis_status.pop(vacancy_id, None)
                self.save_analysis_status()
                self.update_table()

    def check_analysis_status(self, vacancy_id):
        """Проверяет статус анализа при закрытии окна"""
        # Если окно закрылось, а статус все еще 'in_progress', значит анализ был прерван
        if self.analysis_status.get(vacancy_id) == 'in_progress':
            self.analysis_status[vacancy_id] = 'interrupted'
            self.save_analysis_status()
            self.update_table()

    def load_from_cache(self):
        """Загружает результаты анализа из кэша"""
        row = self.table.currentRow()
        if row >= 0:
            try:
                from ai_agent_window import AIAgentWindow
                vacancy = self.vacancies[row]
                self.ai_window = AIAgentWindow(vacancy)
                self.ai_window.load_from_cache()  # Вызываем метод загрузки из кэша
                self.ai_window.show()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить из кэша: {str(e)}")

    def mark_vacancy_analyzed(self, vacancy_id, status='completed'):
        """Отмечает вакансию как проанализированную"""
        if vacancy_id:
            self.analysis_status[vacancy_id] = status
            self.save_analysis_status()
            self.update_table()

    def create_offer_for_best_candidate(self, vacancy):
        """Создает оффер для лучшего кандидата"""
        vacancy_id = str(vacancy.get('id'))
        
        # Проверяем наличие файла с результатами анализа
        cache_file = f"analysis_cache_{vacancy_id}.json"
        if not os.path.exists(cache_file):
            QMessageBox.warning(self, "Ошибка", "Файл с результатами анализа не найден")
            return
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            if not results:
                QMessageBox.warning(self, "Ошибка", "Нет результатов анализа")
                return
            
            # Берем лучшего кандидата
            best_candidate = results[0]['candidate']
            
            reply = QMessageBox.question(
                self,
                "Создание оффера",
                f"Вы хотите создать оффер для лучшего кандидата?\n\n"
                f"🏆 {self.format_candidate_name(best_candidate)}\n"
                f"📊 Рейтинг: {results[0]['score']}%\n\n"
                f"Продолжить?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.open_offer_window(vacancy, best_candidate)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить результаты: {str(e)}")

    def create_offer_for_selected_candidate(self, vacancy):
        """Создает оффер для выбранного кандидата из топа"""
        vacancy_id = str(vacancy.get('id'))
        
        cache_file = f"analysis_cache_{vacancy_id}.json"
        if not os.path.exists(cache_file):
            QMessageBox.warning(self, "Ошибка", "Файл с результатами анализа не найден")
            return
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            if not results:
                QMessageBox.warning(self, "Ошибка", "Нет результатов анализа")
                return
            
            # Формируем список кандидатов для выбора
            candidates_list = []
            for i, r in enumerate(results[:10], 1):
                candidate = r['candidate']
                name = self.format_candidate_name(candidate)
                candidates_list.append(f"{i}. {name} (рейтинг: {r['score']}%)")
            
            # Запрашиваем номер кандидата
            number, ok = QInputDialog.getItem(
                self,
                "Выбор кандидата",
                "Выберите кандидата из топа:",
                candidates_list,
                0,
                False
            )
            
            if ok and number:
                # Извлекаем индекс
                try:
                    index = int(number.split('.')[0]) - 1
                    if 0 <= index < len(results):
                        selected_candidate = results[index]['candidate']
                        self.open_offer_window(vacancy, selected_candidate)
                except:
                    QMessageBox.warning(self, "Ошибка", "Не удалось определить кандидата")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить результаты: {str(e)}")

    def format_candidate_name(self, candidate):
        """Форматирует имя кандидата"""
        if 'first_name' in candidate and 'last_name' in candidate:
            return f"{candidate.get('last_name', '')} {candidate.get('first_name', '')}".strip()
        return candidate.get('name', 'Неизвестно')

    def open_offer_window(self, vacancy, candidate):
        """Открывает окно создания оффера"""
        try:
            from document_window import DocumentWindow
            self.offer_window = DocumentWindow(vacancy, candidate)
            self.offer_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть окно оффера: {str(e)}")

    def load_vacancies(self):
        """Загрузка вакансий из JSON файла"""
        try:
            with open('vacancy_test_file.json', 'r', encoding='utf-8') as f:
                self.vacancies = json.load(f)

            self.update_table()
            self.count_label.setText(f"Всего вакансий: {len(self.vacancies)}")

        except FileNotFoundError:
            QMessageBox.warning(self, "Предупреждение",
                                "Файл vacancy_test_file.json не найден. Загрузите данные через 'Обновление данных'.")
            self.count_label.setText("Файл не найден")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить вакансии: {str(e)}")
            self.count_label.setText("Ошибка загрузки данных")

    def update_table(self):
        """Обновление таблицы данными с цветовой индикацией"""
        self.table.setRowCount(len(self.vacancies))

        for row, vacancy in enumerate(self.vacancies):
            vacancy_id = str(vacancy.get('id', ''))
            
            # ID
            self.table.setItem(row, 0, QTableWidgetItem(vacancy_id))

            # Название
            title_item = QTableWidgetItem(vacancy.get('title', ''))
            title_item.setToolTip(vacancy.get('title', ''))
            self.table.setItem(row, 1, title_item)

            # Зарплата
            salary = vacancy.get('salary', '')
            if isinstance(salary, dict):
                salary_from = salary.get('from', '')
                salary_to = salary.get('to', '')
                salary_currency = salary.get('currency', '')
                if salary_from and salary_to:
                    salary_text = f"{salary_from} - {salary_to} {salary_currency}"
                elif salary_from:
                    salary_text = f"от {salary_from} {salary_currency}"
                elif salary_to:
                    salary_text = f"до {salary_to} {salary_currency}"
                else:
                    salary_text = "Не указана"
            else:
                salary_text = str(salary) if salary else "Не указана"
            self.table.setItem(row, 2, QTableWidgetItem(salary_text))

            # Город
            area = vacancy.get('area', {})
            if isinstance(area, dict):
                city = area.get('name', 'Не указан')
            else:
                city = str(area) if area else "Не указан"
            self.table.setItem(row, 3, QTableWidgetItem(city))

            # Опыт
            experience = vacancy.get('experience', {})
            if isinstance(experience, dict):
                exp_text = experience.get('name', 'Не указан')
            else:
                exp_text = str(experience) if experience else "Не указан"
            self.table.setItem(row, 4, QTableWidgetItem(exp_text))

            # График
            schedule = vacancy.get('schedule', {})
            if isinstance(schedule, dict):
                schedule_text = schedule.get('name', 'Не указан')
            else:
                schedule_text = str(schedule) if schedule else "Не указан"
            self.table.setItem(row, 5, QTableWidgetItem(schedule_text))

            # Занятость
            employment = vacancy.get('employment', {})
            if isinstance(employment, dict):
                employment_text = employment.get('name', 'Не указана')
            else:
                employment_text = str(employment) if employment else "Не указана"
            self.table.setItem(row, 6, QTableWidgetItem(employment_text))

            # Дата публикации
            date_str = vacancy.get('published_at', '')
            if date_str:
                try:
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    date_str = date.strftime('%d.%m.%Y')
                except:
                    pass
            self.table.setItem(row, 7, QTableWidgetItem(date_str))

            # Навыки
            skills = vacancy.get('skills', [])
            if isinstance(skills, list):
                skills_text = ", ".join([s.get('name', '') if isinstance(s, dict) else str(s) for s in skills[:5]])
                if len(skills) > 5:
                    skills_text += f" и еще {len(skills) - 5}"
            else:
                skills_text = str(skills) if skills else "Не указаны"
            skills_item = QTableWidgetItem(skills_text)
            skills_item.setToolTip(skills_text)
            self.table.setItem(row, 8, skills_item)
            
            # Статус анализа
            status = self.analysis_status.get(vacancy_id, 'not_started')
            
            if status == 'completed':
                status_item = QTableWidgetItem("✅ Анализ завершен")
                status_item.setForeground(QColor(styles.S7_GREEN))
                # Подсвечиваем всю строку бледно-зеленым
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor(240, 255, 240))
            elif status == 'in_progress':
                status_item = QTableWidgetItem("⏳ Анализируется...")
                status_item.setForeground(QColor("#FFA500"))
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor(255, 255, 200))
            elif status == 'interrupted':
                status_item = QTableWidgetItem("⚠️ Анализ прерван")
                status_item.setForeground(QColor(styles.S7_RED))
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(QColor(255, 220, 220))
            else:
                status_item = QTableWidgetItem("⏳ Не проводился")
                status_item.setForeground(QColor(styles.S7_GRAY))
            
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 9, status_item)