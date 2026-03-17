# -*- coding: utf-8 -*-
"""
Окно расписания собеседований с ИИ-ассистентом
"""
import json
import os
from datetime import datetime, timedelta, date
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QCalendarWidget, QTableWidget, QTableWidgetItem,
                             QPushButton, QMessageBox, QGroupBox, QHeaderView,
                             QComboBox, QTimeEdit, QTextEdit, QLineEdit,
                             QDialog, QDialogButtonBox, QFormLayout, QSpinBox,
                             QTabWidget, QSplitter, QFrame, QFileDialog,
                             QDateEdit, QMenu)
from PyQt5.QtCore import Qt, QDate, QTime, pyqtSignal, QRect, QSize
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QTextCharFormat, QCursor
import styles
from ai_schedule_manager import AIScheduleManager


class InterviewCalendarWidget(QCalendarWidget):
    """Календарь с отображением количества собеседований"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.interview_counts = {}
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        
    def set_interview_counts(self, counts):
        """Устанавливает данные о количестве собеседований"""
        self.interview_counts = counts
        self.updateCells()
        
    def paintCell(self, painter, rect, date):
        """Переопределяем отрисовку ячейки для отображения количества"""
        super().paintCell(painter, rect, date)
        
        date_str = date.toString("yyyy-MM-dd")
        count = self.interview_counts.get(date_str, 0)
        
        if count > 0:
            # Сохраняем состояние painter
            painter.save()
            
            # Устанавливаем цвет в зависимости от количества
            if count >= 15:
                painter.setBrush(QBrush(QColor(255, 200, 200)))  # Бледно-красный
                painter.setPen(QPen(Qt.red))
            else:
                painter.setBrush(QBrush(QColor(200, 255, 200)))  # Светло-зеленый
                painter.setPen(QPen(QColor(styles.S7_GREEN)))
            
            # Рисуем круг с количеством
            text_rect = QRect(rect.right() - 25, rect.top() + 2, 20, 20)
            painter.drawEllipse(text_rect)
            
            # Рисуем текст
            painter.setPen(QPen(Qt.black))
            painter.drawText(text_rect, Qt.AlignCenter, str(count))
            
            painter.restore()


class AddInterviewDialog(QDialog):
    """Диалог добавления собеседования"""
    
    def __init__(self, user_data, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("➕ Добавление собеседования")
        self.setGeometry(300, 300, 400, 350)
        self.setStyleSheet(styles.MAIN_STYLE)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        form_layout = QFormLayout()
        
        # Дата
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate().addDays(1))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumDate(QDate.currentDate())
        form_layout.addRow("📅 Дата:", self.date_edit)
        
        # Время
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime(10, 0))
        self.time_edit.setDisplayFormat("HH:mm")
        form_layout.addRow("⏰ Время:", self.time_edit)
        
        # Кандидат
        self.candidate_input = QLineEdit()
        self.candidate_input.setPlaceholderText("Введите ФИО кандидата")
        form_layout.addRow("👤 Кандидат:", self.candidate_input)
        
        # Интервьюер (автоматически заполняется текущим пользователем)
        self.interviewer_input = QLineEdit()
        self.interviewer_input.setText(self.user_data.get('username', 'Не назначен'))
        self.interviewer_input.setReadOnly(True)  # Делаем только для чтения
        self.interviewer_input.setStyleSheet("background-color: #f0f0f0;")
        form_layout.addRow("👥 Интервьюер:", self.interviewer_input)
        
        # Комментарий
        self.comment_input = QTextEdit()
        self.comment_input.setMaximumHeight(80)
        self.comment_input.setPlaceholderText("Дополнительная информация...")
        form_layout.addRow("📝 Комментарий:", self.comment_input)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_data(self):
        """Возвращает введенные данные"""
        return {
            'date': self.date_edit.date().toString("yyyy-MM-dd"),
            'time': self.time_edit.time().toString("HH:mm"),
            'candidate': self.candidate_input.text().strip(),
            'interviewer': self.interviewer_input.text().strip(),
            'comment': self.comment_input.toPlainText().strip()
        }


class ScheduleWindow(QWidget):
    """Окно расписания собеседований с ИИ-ассистентом"""

    SCHEDULE_FILE = "interviews_schedule.json"

    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.interviews = self.load_interviews()
        self.ai_agent = AIScheduleManager()
        self.init_ui()
        self.update_interviews_list()
        self.update_calendar_counts()

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("S7 Recruitment - Расписание собеседований")
        self.setGeometry(200, 200, 1300, 700)
        self.setStyleSheet(styles.MAIN_STYLE)

        # Основной layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Левая панель (календарь)
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

        # Заголовок
        header_label = QLabel("📅 Календарь собеседований")
        header_label.setObjectName("headerLabel")
        left_layout.addWidget(header_label)

        # Календарь
        self.calendar = InterviewCalendarWidget()
        self.calendar.clicked.connect(self.date_selected)
        self.calendar.setMinimumHeight(250)
        left_layout.addWidget(self.calendar)

        # Информация о выбранной дате
        date_group = QGroupBox("Выбранная дата")
        date_layout = QVBoxLayout()

        self.selected_date_label = QLabel()
        self.selected_date_label.setStyleSheet(f"font-size: 14px; color: {styles.S7_GREEN};")
        date_layout.addWidget(self.selected_date_label)

        date_group.setLayout(date_layout)
        left_layout.addWidget(date_group)

        # Кнопка добавления
        add_btn = QPushButton("➕ Добавить собеседование")
        add_btn.clicked.connect(self.show_add_dialog)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setMinimumHeight(40)
        left_layout.addWidget(add_btn)

        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(350)

        # Центральная панель (таблица собеседований)
        center_panel = QWidget()
        center_layout = QVBoxLayout()
        center_layout.setSpacing(10)

        # Заголовок таблицы
        table_header = QLabel("📋 Собеседования на выбранную дату")
        table_header.setObjectName("headerLabel")
        center_layout.addWidget(table_header)

        # Таблица
        self.interviews_table = QTableWidget()
        self.interviews_table.setColumnCount(6)  # Убрали колонку с ID, теперь будет невидимая
        self.interviews_table.setHorizontalHeaderLabels(
            ["Время", "Кандидат", "Интервьюер", "Комментарий", "Статус", "Действия"]
        )

        # Настройка растягивания колонок
        header = self.interviews_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Время
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Кандидат - растягивается
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Интервьюер
        header.setSectionResizeMode(3, QHeaderView.Stretch)  # Комментарий - растягивается
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Статус
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Действия

        # Устанавливаем минимальную ширину для ключевых колонок
        self.interviews_table.setColumnWidth(1, 250)  # Кандидат
        self.interviews_table.setColumnWidth(2, 150)  # Интервьюер
        self.interviews_table.setColumnWidth(3, 200)  # Комментарий
        self.interviews_table.setColumnWidth(4, 120)  # Статус

        self.interviews_table.setAlternatingRowColors(True)
        self.interviews_table.setWordWrap(True)
        self.interviews_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Включаем контекстное меню
        self.interviews_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.interviews_table.customContextMenuRequested.connect(self.show_interview_context_menu)
        
        center_layout.addWidget(self.interviews_table)

        # Кнопка обновления
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.update_interviews_list)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        center_layout.addWidget(refresh_btn)

        center_panel.setLayout(center_layout)

        # Правая панель (ИИ-ассистент и статистика)
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)

        # ИИ-ассистент
        ai_group = QGroupBox("🤖 ИИ-ассистент")
        ai_layout = QVBoxLayout()

        # Статус ИИ
        self.ai_status = QLabel("✅ ИИ активен")
        self.ai_status.setStyleSheet(f"color: {styles.S7_GREEN};")
        ai_layout.addWidget(self.ai_status)

        # Авто-назначение
        auto_group = QGroupBox("Авто-назначение")
        auto_layout = QVBoxLayout()
        
        self.auto_candidate = QLineEdit()
        self.auto_candidate.setPlaceholderText("Введите имя кандидата")
        auto_layout.addWidget(self.auto_candidate)
        
        auto_btn = QPushButton("🎯 Назначить время")
        auto_btn.clicked.connect(self.auto_schedule)
        auto_btn.setCursor(Qt.PointingHandCursor)
        auto_layout.addWidget(auto_btn)
        
        auto_group.setLayout(auto_layout)
        ai_layout.addWidget(auto_group)

        # Кнопка анализа конфликтов
        self.analyze_conflicts_btn = QPushButton("🔍 Проверить конфликты")
        self.analyze_conflicts_btn.clicked.connect(self.analyze_conflicts)
        self.analyze_conflicts_btn.setCursor(Qt.PointingHandCursor)
        ai_layout.addWidget(self.analyze_conflicts_btn)

        ai_group.setLayout(ai_layout)
        right_layout.addWidget(ai_group)

        # Статистика
        stats_group = QGroupBox("📊 Статистика")
        stats_layout = QVBoxLayout()

        self.stats_label = QLabel("Загрузка...")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)

        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)

        # Советы
        tips_group = QGroupBox("💡 Советы")
        tips_layout = QVBoxLayout()

        tips = [
            "• Лучшее время: 10:00-12:00",
            "• Оставляйте 30 мин между собеседованиями",
            "• Учитывайте часовые пояса",
            "• Подтверждайте за день",
            "• При превышении 15 собеседований день помечается красным"
        ]

        for tip in tips:
            tips_layout.addWidget(QLabel(tip))

        tips_group.setLayout(tips_layout)
        right_layout.addWidget(tips_group)

        right_layout.addStretch()
        right_panel.setLayout(right_layout)
        right_panel.setMaximumWidth(300)

        # Добавляем панели
        main_layout.addWidget(left_panel)
        main_layout.addWidget(center_panel, 1)
        main_layout.addWidget(right_panel)

        self.setLayout(main_layout)

        # Установка текущей даты
        self.date_selected(self.calendar.selectedDate())

    def load_interviews(self):
        """Загрузка собеседований из файла"""
        if os.path.exists(self.SCHEDULE_FILE):
            try:
                with open(self.SCHEDULE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_interviews(self):
        """Сохранение собеседований в файл"""
        try:
            with open(self.SCHEDULE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.interviews, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить расписание: {str(e)}")

    def update_calendar_counts(self):
        """Обновляет счетчики на календаре"""
        counts = {}
        for date_str, interviews in self.interviews.items():
            counts[date_str] = len(interviews)
        self.calendar.set_interview_counts(counts)

    def date_selected(self, date):
        """Обработка выбора даты"""
        date_str = date.toString("yyyy-MM-dd")
        self.selected_date_label.setText(f"Выбрана: {date.toString('dd.MM.yyyy')}")
        self.update_interviews_for_date(date_str)

    def show_add_dialog(self):
        """Показывает диалог добавления собеседования"""
        dialog = AddInterviewDialog(self.user_data, self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            self.add_interview(data)

    def add_interview(self, data):
        """Добавление нового собеседования"""
        date_str = data['date']
        time_str = data['time']
        candidate = data['candidate']
        interviewer = data['interviewer']
        comment = data['comment']

        if not candidate:
            QMessageBox.warning(self, "Предупреждение", "Введите имя кандидата")
            return

        # Проверка на прошедшее время
        current_datetime = datetime.now()
        interview_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        
        if interview_datetime < current_datetime:
            QMessageBox.warning(self, "Ошибка", "Нельзя назначать собеседование на прошедшее время")
            return

        # Проверка на конфликт
        existing = self.interviews.get(date_str, [])
        if any(i.get('time') == time_str for i in existing):
            QMessageBox.warning(self, "Конфликт", f"Время {time_str} уже занято!")
            return

        # Создаем ID для собеседования
        interview_id = f"int_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        new_interview = {
            'id': interview_id,
            'candidate': candidate,
            'time': time_str,
            'date': date_str,
            'comment': comment,
            'interviewer': interviewer,
            'created_by': self.user_data.get('username'),
            'created_at': datetime.now().isoformat(),
            'status': 'scheduled'
        }

        if date_str not in self.interviews:
            self.interviews[date_str] = []

        self.interviews[date_str].append(new_interview)
        self.save_interviews()

        # Отправляем уведомление
        self.ai_agent.send_interview_notification(new_interview)

        # Обновление
        self.update_interviews_for_date(date_str)
        self.update_interviews_list()
        self.update_calendar_counts()

        QMessageBox.information(
            self,
            "Успех",
            f"✅ Собеседование для кандидата {candidate} добавлено на {date_str} в {time_str}\n"
            f"👥 Интервьюер: {interviewer}"
        )

    def update_interviews_for_date(self, date_str):
        """Обновление списка собеседований для выбранной даты"""
        self.interviews_table.setRowCount(0)

        interviews = self.interviews.get(date_str, [])
        interviews.sort(key=lambda x: x.get('time', ''))

        for row, interview in enumerate(interviews):
            self.interviews_table.insertRow(row)

            # Сохраняем ID как скрытые данные
            id_item = QTableWidgetItem(interview.get('id', ''))
            id_item.setData(Qt.UserRole, interview.get('id', ''))

            # Время
            time_item = QTableWidgetItem(interview.get('time', ''))
            time_item.setTextAlignment(Qt.AlignCenter)
            self.interviews_table.setItem(row, 0, time_item)

            # Кандидат (с полным ФИО)
            candidate_name = interview.get('candidate', '')
            candidate_item = QTableWidgetItem(candidate_name)
            candidate_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            candidate_item.setToolTip(candidate_name)
            # Если имя слишком длинное, оно автоматически обрежется с "..."
            self.interviews_table.setItem(row, 1, candidate_item)

            # Интервьюер
            interviewer = interview.get('interviewer', 'Не назначен')
            interviewer_item = QTableWidgetItem(interviewer)
            interviewer_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            if interviewer == self.user_data.get('username'):
                interviewer_item.setForeground(QColor(styles.S7_GREEN))
                interviewer_item.setFont(self.font())  # Можно сделать жирным при необходимости
            interviewer_item.setToolTip(interviewer)
            self.interviews_table.setItem(row, 2, interviewer_item)

            # Комментарий
            comment = interview.get('comment', '')
            comment_item = QTableWidgetItem(comment)
            comment_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            comment_item.setToolTip(comment)
            self.interviews_table.setItem(row, 3, comment_item)

            # Статус
            status = interview.get('status', 'scheduled')
            status_text = {
                'scheduled': 'Запланировано',
                'rescheduled': 'Перенесено',
                'cancelled': 'Отменено',
                'completed': 'Завершено'
            }.get(status, status)

            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            if status == 'scheduled':
                status_item.setForeground(QColor(styles.S7_GREEN))
            elif status == 'rescheduled':
                status_item.setForeground(QColor("#FFA500"))
            elif status == 'cancelled':
                status_item.setForeground(QColor(styles.S7_RED))
            self.interviews_table.setItem(row, 4, status_item)

            # Кнопки действий
            widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(2)

            # Кнопка деталей
            details_btn = QPushButton("👁️")
            details_btn.setFixedSize(25, 25)
            details_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {styles.S7_LIGHT_GREEN};
                    color: white;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: {styles.S7_GREEN};
                }}
            """)
            details_btn.clicked.connect(lambda checked, i=interview: self.show_interview_details(i))
            details_btn.setToolTip("Просмотреть детали")
            btn_layout.addWidget(details_btn)

            # Кнопка переноса
            reschedule_btn = QPushButton("🔄")
            reschedule_btn.setFixedSize(25, 25)
            reschedule_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #FFA500;
                    color: white;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: #FF8C00;
                }}
            """)
            reschedule_btn.clicked.connect(lambda checked, i=interview: self.request_reschedule(i))
            reschedule_btn.setToolTip("Запросить перенос")
            btn_layout.addWidget(reschedule_btn)

            # Кнопка удаления
            if interview.get('interviewer') == self.user_data.get('username') or self.user_data.get('role') == 'admin':
                delete_btn = QPushButton("✖")
                delete_btn.setFixedSize(25, 25)
                delete_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {styles.S7_RED};
                        color: white;
                        border-radius: 4px;
                    }}
                    QPushButton:hover {{
                        background-color: {styles.S7_RED};
                        opacity: 0.8;
                    }}
                """)
                delete_btn.clicked.connect(lambda checked, d=date_str, i=interview: self.delete_interview(d, i))
                delete_btn.setToolTip("Удалить")
                btn_layout.addWidget(delete_btn)

            btn_layout.addStretch()
            widget.setLayout(btn_layout)
            self.interviews_table.setCellWidget(row, 5, widget)

        # Автоматически подгоняем высоту строк под содержимое
        self.interviews_table.resizeRowsToContents()

    def update_interviews_list(self):
        """Обновление всего списка"""
        date_str = self.calendar.selectedDate().toString("yyyy-MM-dd")
        self.update_interviews_for_date(date_str)

        # Получаем статистику от ИИ
        stats = self.ai_agent.get_schedule_statistics()

        stats_text = f"""
📈 ОБЩАЯ СТАТИСТИКА
━━━━━━━━━━━━━━━━
Всего собеседований: {stats.get('total_interviews', 0)}
Дней с собесед.: {stats.get('days_with_interviews', 0)}
Ср. в день: {stats.get('average_per_day', 0):.1f}

📊 СТАТУСЫ:
• Запланировано: {stats.get('status_stats', {}).get('scheduled', 0)}
• Перенесено: {stats.get('status_stats', {}).get('rescheduled', 0)}

📬 СООБЩЕНИЯ:
• Непрочитанных: {stats.get('message_stats', {}).get('unread', 0)}
• Ожидают: {stats.get('message_stats', {}).get('pending_requests', 0)}
"""
        self.stats_label.setText(stats_text)

    def auto_schedule(self):
        """Автоматическое назначение времени для кандидата"""
        candidate = self.auto_candidate.text().strip()
        if not candidate:
            QMessageBox.warning(self, "Ошибка", "Введите имя кандидата")
            return

        # Простые данные кандидата
        candidate_data = {
            "name": candidate,
            "city": "Москва"
        }

        # Запрашиваем авто-назначение
        result = self.ai_agent.auto_schedule_offer(
            candidate,
            candidate_data,
            self.user_data.get('username')
        )

        if result.get('success'):
            # Автоматически добавляем в расписание
            reply = QMessageBox.question(
                self,
                "Рекомендация ИИ",
                f"🤖 ИИ рекомендует:\n\n"
                f"📅 Дата: {result['date']}\n"
                f"⏰ Время: {result['time']}\n"
                f"📊 Уверенность: {result.get('confidence', 0)}%\n"
                f"💬 Причина: {result.get('reason', '')}\n\n"
                f"Добавить в расписание?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # Создаем собеседование
                interview_id = f"int_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                new_interview = {
                    'id': interview_id,
                    'candidate': candidate,
                    'time': result['time'],
                    'date': result['date'],
                    'comment': f"Авто-назначение от ИИ. {result.get('reason', '')}",
                    'interviewer': self.user_data.get('username'),
                    'created_by': 'AI Agent',
                    'created_at': datetime.now().isoformat(),
                    'status': 'scheduled'
                }

                if result['date'] not in self.interviews:
                    self.interviews[result['date']] = []

                self.interviews[result['date']].append(new_interview)
                self.save_interviews()
                self.ai_agent.send_interview_notification(new_interview)
                self.update_calendar_counts()

                QMessageBox.information(
                    self, 
                    "Успех", 
                    f"✅ Собеседование для кандидата {candidate} добавлено!\n"
                    f"👥 Интервьюер: {self.user_data.get('username')}"
                )
                self.update_interviews_list()
                
            self.auto_candidate.clear()
        else:
            QMessageBox.warning(
                self,
                "Нет свободных слотов",
                f"Не удалось найти время.\n"
                f"Предложения: {', '.join(result.get('suggestions', []))}"
            )

    def show_interview_context_menu(self, pos):
        """Показать контекстное меню для собеседования"""
        row = self.interviews_table.currentRow()
        if row < 0:
            return
        
        # Получаем данные собеседования
        date_str = self.calendar.selectedDate().toString("yyyy-MM-dd")
        
        # Находим собеседование по времени (так как ID скрыт)
        time_str = self.interviews_table.item(row, 0).text()
        
        interview = None
        for i in self.interviews.get(date_str, []):
            if i.get('time') == time_str and i.get('candidate') == self.interviews_table.item(row, 1).text():
                interview = i
                break
        
        if not interview:
            return
        
        menu = QMenu()
        
        # Просмотр деталей
        view_action = menu.addAction("👁️ Просмотреть детали")
        view_action.triggered.connect(lambda: self.show_interview_details(interview))
        
        menu.addSeparator()
        
        # Отправка на email
        # Отправка на email (доступна только если файл прикреплен)
        offer_file = interview.get('offer_file')
        if offer_file and os.path.exists(offer_file):
            email_action = menu.addAction("✉️ Отправить приглашение на email")
            email_action.triggered.connect(lambda: self.send_invitation_email(interview))
        else:
            # Добавляем неактивный пункт для информации
            email_action = menu.addAction("✉️ Отправить приглашение (сначала прикрепите файл)")
            email_action.setEnabled(False)
        
        # Прикрепить файл с оффером
        attach_action = menu.addAction("📎 Прикрепить файл с оффером")
        attach_action.triggered.connect(lambda: self.attach_offer_file(interview))
        
        menu.addSeparator()
        
        # Запрос на перенос
        reschedule_action = menu.addAction("🔄 Запросить перенос")
        reschedule_action.triggered.connect(lambda: self.request_reschedule(interview))
        
        # Удаление
        if interview.get('interviewer') == self.user_data.get('username') or self.user_data.get('role') == 'admin':
            delete_action = menu.addAction("🗑️ Удалить")
            delete_action.triggered.connect(lambda: self.delete_interview(date_str, interview))
        
        menu.exec_(self.interviews_table.mapToGlobal(pos))

    def send_invitation_email(self, interview):
        """Отправляет приглашение на email"""
        candidate = interview.get('candidate', '')
        
        # Проверяем, прикреплен ли файл с оффером
        offer_file = interview.get('offer_file')
        file_info = ""
        if offer_file and os.path.exists(offer_file):
            file_info = f"\n📎 Прикреплен файл: {os.path.basename(offer_file)}"
        
        # Формируем текст письма
        email_text = f"""Тема: Приглашение на собеседование - {candidate}

Уважаемый(ая) {candidate}!

Вам назначено собеседование на вакансию в S7 Airlines.

📅 Дата: {interview.get('date')}
⏰ Время: {interview.get('time')}
👥 Интервьюер: {interview.get('interviewer', 'Не назначен')}

📝 Комментарий: {interview.get('comment', 'Нет комментария')}

Пожалуйста, подтвердите своё участие ответом на это письмо.

С уважением,
Команда S7 Recruitment
{file_info}
"""
        
        # В демо-версии просто показываем сообщение
        QMessageBox.information(
            self,
            "Отправка приглашения",
            f"✅ Приглашение успешно отправлено кандидату {candidate}\n\n"
            f"{email_text}"
        )

    def attach_offer_file(self, interview):
        """Прикрепляет файл с оффером к собеседованию"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл с оффером",
            "",
            "Word Documents (*.docx);;PDF Files (*.pdf);;All files (*.*)"
        )
        
        if filename:
            # Сохраняем путь к файлу в данных собеседования
            date_str = self.calendar.selectedDate().toString("yyyy-MM-dd")
            for i in self.interviews.get(date_str, []):
                if i.get('id') == interview.get('id'):
                    i['offer_file'] = filename
                    break
            
            self.save_interviews()
            
            QMessageBox.information(
                self,
                "Файл прикреплен",
                f"✅ Файл {os.path.basename(filename)} успешно прикреплен к собеседованию\n"
                f"для кандидата {interview.get('candidate')}"
            )

    def request_reschedule(self, interview):
        """Запрос на перенос собеседования"""
        dialog = RescheduleRequestDialog(interview, self.ai_agent, self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_interviews_list()
            QMessageBox.information(
                self,
                "Запрос отправлен",
                f"✅ Запрос на перенос для кандидата {interview.get('candidate')} отправлен другой стороне"
            )

    def delete_interview(self, date_str, interview):
        """Удаление собеседования"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить собеседование с {interview.get('candidate')}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if date_str in self.interviews:
                self.interviews[date_str] = [
                    i for i in self.interviews[date_str]
                    if i.get('id') != interview.get('id')
                ]

                if not self.interviews[date_str]:
                    del self.interviews[date_str]

                self.save_interviews()
                self.update_interviews_for_date(date_str)
                self.update_interviews_list()
                self.update_calendar_counts()

    def show_interview_details(self, interview):
        """Показывает детали собеседования"""
        details = f"""
📋 ДЕТАЛИ СОБЕСЕДОВАНИЯ
━━━━━━━━━━━━━━━━━━━━━━━

👤 Кандидат: {interview.get('candidate')}
👥 Интервьюер: {interview.get('interviewer', 'Не назначен')}
📅 Дата: {interview.get('date')}
⏰ Время: {interview.get('time')}
📊 Статус: {interview.get('status', 'scheduled')}

📝 Комментарий:
{interview.get('comment', 'Нет комментария')}

🆔 ID: {interview.get('id')}
📅 Создано: {interview.get('created_at', '')[:10]}
"""
        if 'previous_date' in interview:
            details += f"\n🔄 Перенесено с: {interview.get('previous_date')} {interview.get('previous_time')}"
        
        if interview.get('offer_file'):
            details += f"\n📎 Прикреплен файл: {os.path.basename(interview.get('offer_file'))}"

        QMessageBox.information(self, "Детали собеседования", details)

    def analyze_conflicts(self):
        """Анализирует конфликты и ошибки в расписании"""
        conflicts = []
        errors = []
        current_datetime = datetime.now()

        for date_str, interviews in self.interviews.items():
            times = {}
            for i in interviews:
                # Проверка на дублирование времени
                time = i.get('time')
                if time in times:
                    conflicts.append({
                        'date': date_str,
                        'time': time,
                        'interviews': [times[time], i]
                    })
                else:
                    times[time] = i
                
                # Проверка на прошедшее время
                try:
                    interview_datetime = datetime.strptime(f"{date_str} {time}", "%Y-%m-%d %H:%M")
                    if interview_datetime < current_datetime:
                        errors.append({
                            'date': date_str,
                            'time': time,
                            'candidate': i.get('candidate'),
                            'error': 'Собеседование назначено на прошедшее время'
                        })
                except:
                    errors.append({
                        'date': date_str,
                        'time': time,
                        'candidate': i.get('candidate'),
                        'error': 'Некорректный формат даты/времени'
                    })
                
                # Проверка наличия имени кандидата
                if not i.get('candidate') or i.get('candidate').strip() == '':
                    errors.append({
                        'date': date_str,
                        'time': time,
                        'candidate': 'Не указан',
                        'error': 'Не указано имя кандидата'
                    })
                
                # Проверка наличия интервьюера
                if not i.get('interviewer') or i.get('interviewer').strip() == '':
                    errors.append({
                        'date': date_str,
                        'time': time,
                        'candidate': i.get('candidate'),
                        'error': 'Не назначен интервьюер'
                    })

        # Формируем отчет
        report = ""
        
        if conflicts:
            report += "🔴 НАЙДЕНЫ КОНФЛИКТЫ ВРЕМЕНИ:\n\n"
            for c in conflicts:
                report += f"📅 {c['date']} в {c['time']}:\n"
                for i in c['interviews']:
                    report += f"  • {i.get('candidate')} ({i.get('interviewer')})\n"
                report += "\n"
        
        if errors:
            if report:
                report += "\n" + "="*50 + "\n\n"
            report += "⚠️ ОШИБКИ В НАЗНАЧЕНИЯХ:\n\n"
            for e in errors:
                report += f"📅 {e['date']} {e['time']} - {e['candidate']}\n"
                report += f"   ❌ {e['error']}\n\n"
        
        if not conflicts and not errors:
            QMessageBox.information(self, "Анализ", "✅ Конфликтов и ошибок не найдено")
        else:
            QMessageBox.warning(self, "Результаты анализа", report)


class RescheduleRequestDialog(QDialog):
    """Диалог запроса на перенос"""

    def __init__(self, interview, ai_agent, parent=None):
        super().__init__(parent)
        self.interview = interview
        self.ai_agent = ai_agent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Запрос на перенос собеседования")
        self.setGeometry(300, 300, 400, 300)
        self.setStyleSheet(styles.MAIN_STYLE)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Информация
        info_group = QGroupBox("Собеседование")
        info_layout = QFormLayout()

        info_layout.addRow("Кандидат:", QLabel(self.interview.get('candidate', '')))
        info_layout.addRow("Текущее время:", QLabel(f"{self.interview.get('date')} {self.interview.get('time')}"))

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Причина
        reason_group = QGroupBox("Причина переноса")
        reason_layout = QVBoxLayout()

        self.reason_combo = QComboBox()
        self.reason_combo.addItems([
            "Кандидат просит перенести",
            "Интервьюер недоступен",
            "Технические проблемы",
            "Конфликт в расписании",
            "Другое"
        ])
        reason_layout.addWidget(self.reason_combo)

        self.reason_text = QTextEdit()
        self.reason_text.setPlaceholderText("Подробное описание...")
        self.reason_text.setMaximumHeight(80)
        reason_layout.addWidget(self.reason_text)

        reason_group.setLayout(reason_layout)
        layout.addWidget(reason_group)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.send_request)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def send_request(self):
        """Отправляет запрос на перенос"""
        reason = self.reason_combo.currentText()
        if self.reason_text.toPlainText().strip():
            reason += f": {self.reason_text.toPlainText().strip()}"

        result = self.ai_agent.request_reschedule(
            self.interview.get('id'),
            reason,
            self.parent().user_data.get('username', 'Пользователь')
        )

        if result.get('success'):
            QMessageBox.information(self, "Успех", result.get('message'))
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", result.get('message'))