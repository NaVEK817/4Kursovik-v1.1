# -*- coding: utf-8 -*-
"""
Окно сообщений и уведомлений для пользователей
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem,
                             QGroupBox, QMessageBox, QTextEdit, QDialog,
                             QFormLayout, QComboBox, QDateEdit, QTimeEdit,
                             QDialogButtonBox, QMenu)
from PyQt5.QtCore import Qt, QDate, QTime, QPoint
from PyQt5.QtGui import QColor, QCursor
import styles
from datetime import datetime


class MessagesWindow(QWidget):
    """Окно сообщений и уведомлений"""

    def __init__(self, user_data, schedule_manager):
        super().__init__()
        self.user_data = user_data
        self.manager = schedule_manager
        self.init_ui()
        self.load_messages()

    def init_ui(self):
        self.setWindowTitle("S7 Recruitment - Сообщения и уведомления")
        self.setGeometry(200, 200, 900, 700)
        self.setStyleSheet(styles.MAIN_STYLE)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Заголовок
        header = QLabel("📬 Центр уведомлений и запросов")
        header.setObjectName("headerLabel")
        layout.addWidget(header)

        # Статистика сообщений
        stats_group = QGroupBox("📊 Текущая статистика")
        stats_layout = QHBoxLayout()

        self.stats_label = QLabel("Загрузка...")
        self.stats_label.setStyleSheet(f"font-size: 14px; color: {styles.S7_DARK_GREEN};")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()

        # Кнопка обновления
        refresh_btn = QPushButton("🔄 Обновить список")
        refresh_btn.clicked.connect(self.load_messages)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        stats_layout.addWidget(refresh_btn)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Список сообщений
        messages_group = QGroupBox("📋 Лента сообщений")
        messages_layout = QVBoxLayout()

        self.messages_list = QListWidget()
        self.messages_list.itemClicked.connect(self.on_message_clicked)
        self.messages_list.itemDoubleClicked.connect(self.on_message_double_clicked)
        
        # Включаем контекстное меню
        self.messages_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.messages_list.customContextMenuRequested.connect(self.show_context_menu)
        
        messages_layout.addWidget(self.messages_list)

        messages_group.setLayout(messages_layout)
        layout.addWidget(messages_group)

        # Кнопки действий
        buttons_layout = QHBoxLayout()

        self.mark_read_btn = QPushButton("✓ Отметить как прочитанное")
        self.mark_read_btn.clicked.connect(self.mark_selected_read)
        self.mark_read_btn.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.mark_read_btn)

        self.respond_btn = QPushButton("✏️ Ответить на запрос")
        self.respond_btn.clicked.connect(self.respond_to_request)
        self.respond_btn.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.respond_btn)

        self.delete_btn = QPushButton("🗑️ Удалить сообщение")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.S7_RED};
                color: white;
            }}
            QPushButton:hover {{
                background-color: {styles.S7_RED};
                opacity: 0.8;
            }}
        """)
        buttons_layout.addWidget(self.delete_btn)

        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def load_messages(self):
        """Загружает сообщения пользователя"""
        self.messages_list.clear()

        messages = self.manager.get_user_messages(self.user_data.get('username'))

        # Обновляем статистику
        stats = self.manager.get_schedule_statistics()
        msg_stats = stats.get('message_stats', {})

        self.stats_label.setText(
            f"📨 Всего сообщений: {msg_stats.get('total', 0)} | "
            f"🔴 Непрочитанных: {msg_stats.get('unread', 0)} | "
            f"⏳ Ожидают ответа: {msg_stats.get('pending_requests', 0)}"
        )

        for msg in messages:
            self.add_message_to_list(msg)

    def add_message_to_list(self, message: dict):
        """Добавляет сообщение в список с улучшенным форматированием"""
        msg_type = message.get('type', 'notification')
        created = message.get('created_at', '')
        try:
            created_str = datetime.fromisoformat(created).strftime("%d.%m.%Y %H:%M")
        except:
            created_str = created[:16]

        read = message.get('read', False)
        status = message.get('status', '')

        # Формируем иконку и цвет в зависимости от типа
        if msg_type == 'notification':
            if not read:
                prefix = "🔴 НОВОЕ УВЕДОМЛЕНИЕ"
                color = styles.S7_RED
            else:
                prefix = "📢 Уведомление"
                color = styles.S7_GREEN
                
            # Текст уведомления
            msg_text = message.get('message', '')
            short_text = msg_text[:100] + "..." if len(msg_text) > 100 else msg_text
            
            display_text = f"{prefix} | {created_str}\n{short_text}"
            
        elif msg_type == 'reschedule_request':
            interview = message.get('interview_data', {})
            requested_by = message.get('requested_by', 'Неизвестно')
            reason = message.get('reason', 'Причина не указана')[:80]
            
            if status == 'pending':
                prefix = "🟡 ЗАПРОС НА ПЕРЕНОС (ожидает)"
                color = "#FFA500"
            elif status == 'confirmed':
                prefix = "✅ ПЕРЕНОС ПОДТВЕРЖДЁН"
                color = styles.S7_GREEN
            else:
                prefix = "❌ ЗАПРОС ОТКЛОНЁН"
                color = styles.S7_RED
            
            display_text = (f"{prefix} | {created_str}\n"
                          f"👤 От: {requested_by} | 📅 {interview.get('date', '')} {interview.get('time', '')}\n"
                          f"📝 {reason}")
        else:
            prefix = "📝 Сообщение"
            color = styles.S7_BLACK
            display_text = f"{prefix} | {created_str}"

        item = QListWidgetItem(display_text)
        item.setData(Qt.UserRole, message)
        item.setForeground(QColor(color))

        # Устанавливаем высоту элемента
        from PyQt5.QtCore import QSize
        current_size = item.sizeHint()
        item.setSizeHint(QSize(current_size.width(), current_size.height() + 30))

        self.messages_list.addItem(item)

    def show_context_menu(self, pos):
        """Показать контекстное меню для сообщения"""
        item = self.messages_list.itemAt(pos)
        if not item:
            return
            
        message = item.data(Qt.UserRole)
        
        menu = QMenu()
        
        if not message.get('read', False):
            mark_read_action = menu.addAction("✓ Отметить как прочитанное")
            mark_read_action.triggered.connect(lambda: self.mark_message_read(item))
        
        if message.get('type') == 'reschedule_request' and message.get('status') == 'pending':
            respond_action = menu.addAction("✏️ Ответить на запрос")
            respond_action.triggered.connect(lambda: self.respond_to_request())
        
        delete_action = menu.addAction("🗑️ Удалить сообщение")
        delete_action.triggered.connect(lambda: self.delete_message(item))
        
        menu.exec_(self.messages_list.mapToGlobal(pos))

    def on_message_clicked(self, item):
        """Обработка клика по сообщению"""
        message = item.data(Qt.UserRole)

        # Показываем полный текст в зависимости от типа
        if message.get('type') == 'reschedule_request':
            self.show_request_details(message)
        elif message.get('type') == 'notification':
            self.show_notification_details(message)

    def on_message_double_clicked(self, item):
        """Обработка двойного клика"""
        message = item.data(Qt.UserRole)

        if message.get('type') == 'reschedule_request' and message.get('status') == 'pending':
            # Открываем диалог подтверждения переноса
            self.open_reschedule_dialog(message)

    def show_notification_details(self, message):
        """Показывает детали уведомления"""
        QMessageBox.information(
            self,
            "Детали уведомления",
            f"📢 УВЕДОМЛЕНИЕ\n\n"
            f"📅 {message.get('created_at', '')[:16]}\n\n"
            f"{message.get('message', '')}"
        )

    def show_request_details(self, message):
        """Показывает детали запроса с улучшенным форматированием"""
        interview = message.get('interview_data', {})
        alternatives = message.get('suggested_alternatives', [])

        alt_text = "\n".join([f"  • {a['date']} в {a['time']}" for a in alternatives[:3]])

        status_text = {
            'pending': '⏳ Ожидает подтверждения',
            'confirmed': '✅ Подтверждён',
            'rejected': '❌ Отклонён'
        }.get(message.get('status', 'pending'), message.get('status'))

        details = f"""
📋 ЗАПРОС НА ПЕРЕНОС СОБЕСЕДОВАНИЯ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 Запросил: {message.get('requested_by')}
📅 Дата запроса: {message.get('created_at', '')[:16]}
📊 Статус: {status_text}

📝 ПРИЧИНА:
{message.get('reason', 'Не указана')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 ТЕКУЩЕЕ СОБЕСЕДОВАНИЕ:
   • Кандидат: {interview.get('candidate')}
   • Дата: {interview.get('date')}
   • Время: {interview.get('time')}
   • Интервьюер: {interview.get('interviewer')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 ПРЕДЛАГАЕМЫЕ АЛЬТЕРНАТИВЫ:
{alt_text if alt_text else "  Нет предложений"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 ДЕЙСТВИЯ:
   • Двойной клик для подтверждения переноса
   • Кнопка "Ответить" для обработки
   • ПКМ для удаления
"""
        QMessageBox.information(self, "Детали запроса", details)

    def open_reschedule_dialog(self, message):
        """Открывает диалог подтверждения переноса"""
        dialog = RescheduleConfirmDialog(message, self.manager, self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_messages()

    def mark_selected_read(self):
        """Отмечает выбранное сообщение как прочитанное"""
        current = self.messages_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Ошибка", "Выберите сообщение")
            return

        self.mark_message_read(current)

    def mark_message_read(self, item):
        """Отмечает конкретное сообщение как прочитанное"""
        message = item.data(Qt.UserRole)
        self.manager.mark_message_read(message.get('id'))
        self.load_messages()

    def delete_selected(self):
        """Удаляет выбранное сообщение"""
        current = self.messages_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Ошибка", "Выберите сообщение для удаления")
            return

        self.delete_message(current)

    def delete_message(self, item):
        """Удаляет конкретное сообщение"""
        message = item.data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить это сообщение?\n\n{message.get('message', '')[:100]}...",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Загружаем все сообщения
            messages = self.manager._load_messages()
            # Удаляем нужное
            messages = [m for m in messages if m.get('id') != message.get('id')]
            # Сохраняем
            self.manager._save_messages(messages)
            # Обновляем список
            self.load_messages()
            
            QMessageBox.information(self, "Успех", "Сообщение удалено")

    def respond_to_request(self):
        """Отвечает на запрос"""
        current = self.messages_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Ошибка", "Выберите запрос")
            return

        message = current.data(Qt.UserRole)
        if message.get('type') != 'reschedule_request':
            QMessageBox.warning(self, "Ошибка", "Это не запрос на перенос")
            return

        self.open_reschedule_dialog(message)


class RescheduleConfirmDialog(QDialog):
    """Диалог подтверждения переноса"""

    def __init__(self, request, manager, parent=None):
        super().__init__(parent)
        self.request = request
        self.manager = manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Подтверждение переноса собеседования")
        self.setGeometry(300, 300, 500, 400)
        self.setStyleSheet(styles.MAIN_STYLE)

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Информация о запросе
        info_group = QGroupBox("Информация о запросе")
        info_layout = QFormLayout()

        interview = self.request.get('interview_data', {})
        info_layout.addRow("👤 Кандидат:", QLabel(interview.get('candidate', '')))
        info_layout.addRow("📅 Текущая дата:", QLabel(f"{interview.get('date')} {interview.get('time')}"))
        info_layout.addRow("👥 Интервьюер:", QLabel(interview.get('interviewer', '')))
        info_layout.addRow("📝 Причина:", QLabel(self.request.get('reason', '')))

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Выбор новой даты
        date_group = QGroupBox("Выберите новое время")
        date_layout = QFormLayout()

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate().addDays(1))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumDate(QDate.currentDate())
        date_layout.addRow("📅 Новая дата:", self.date_edit)

        self.time_combo = QComboBox()
        self.time_combo.addItems(["09:00", "10:00", "11:00", "12:00", "13:00",
                                  "14:00", "15:00", "16:00", "17:00", "18:00"])
        date_layout.addRow("⏰ Новое время:", self.time_combo)

        date_group.setLayout(date_layout)
        layout.addWidget(date_group)

        # Кнопки
        buttons_layout = QHBoxLayout()

        self.confirm_btn = QPushButton("✅ Подтвердить перенос")
        self.confirm_btn.clicked.connect(self.confirm_reschedule)
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        buttons_layout.addWidget(self.confirm_btn)

        self.reject_btn = QPushButton("❌ Отклонить запрос")
        self.reject_btn.clicked.connect(self.reject_request)
        self.reject_btn.setCursor(Qt.PointingHandCursor)
        self.reject_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.S7_RED};
                color: white;
            }}
        """)
        buttons_layout.addWidget(self.reject_btn)

        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def confirm_reschedule(self):
        """Подтверждает перенос"""
        new_date = self.date_edit.date().toString("yyyy-MM-dd")
        new_time = self.time_combo.currentText()

        result = self.manager.confirm_reschedule(
            self.request.get('id'),
            new_date,
            new_time
        )

        if result.get('success'):
            QMessageBox.information(self, "Успех", result.get('message'))
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", result.get('message'))

    def reject_request(self):
        """Отклоняет запрос"""
        reply = QMessageBox.question(
            self,
            "Отклонение запроса",
            "Вы уверены, что хотите отклонить запрос на перенос?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "Информация", "Запрос отклонен")
            self.reject()