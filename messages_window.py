# -*- coding: utf-8 -*-
"""
Окно сообщений и уведомлений для пользователей
"""
import json
import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem,
                             QGroupBox, QMessageBox, QTextEdit, QDialog,
                             QFormLayout, QComboBox, QDateEdit, QTimeEdit,
                             QDialogButtonBox, QMenu, QProgressBar)
from PyQt5.QtCore import Qt, QDate, QTime, QPoint, QTimer
from PyQt5.QtGui import QColor, QCursor, QFont
import styles

# Константа для файла с сообщениями
MESSAGES_FILE = "interview_messages.json"


class MessagesWindow(QWidget):
    """Окно сообщений и уведомлений"""

    def __init__(self, user_data, schedule_manager):
        super().__init__()
        self.user_data = user_data
        self.manager = schedule_manager
        self.messages_file = MESSAGES_FILE
        self.init_ui()
        self.load_messages()

    def init_ui(self):
        self.setWindowTitle("S7 Recruitment - Сообщения и уведомления")
        self.setGeometry(200, 200, 1000, 750)
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

        # НОВАЯ КНОПКА: Решить все сообщения
        self.resolve_all_btn = QPushButton("✅ Решить все сообщения")
        self.resolve_all_btn.clicked.connect(self.resolve_all_messages)
        self.resolve_all_btn.setCursor(Qt.PointingHandCursor)
        self.resolve_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.S7_GREEN};
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {styles.S7_DARK_GREEN};
            }}
        """)
        buttons_layout.addWidget(self.resolve_all_btn)

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

        # Прогресс бар для массовых операций
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def load_messages_from_file(self):
        """Загружает все сообщения из файла interview_messages.json"""
        if not os.path.exists(self.messages_file):
            return []
        
        try:
            with open(self.messages_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка загрузки сообщений: {e}")
            return []

    def save_messages_to_file(self, messages):
        """Сохраняет все сообщения в файл interview_messages.json"""
        try:
            with open(self.messages_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Ошибка сохранения сообщений: {e}")
            return False

    def get_message_stats(self):
        """Получает статистику сообщений из файла"""
        messages = self.load_messages_from_file()
        
        total = len(messages)
        unread = sum(1 for m in messages if not m.get('read', False))
        pending = sum(1 for m in messages if m.get('status') == 'pending')
        
        return {
            'total': total,
            'unread': unread,
            'pending': pending
        }

    def load_messages(self):
        """Загружает сообщения пользователя"""
        self.messages_list.clear()
        
        # Загружаем все сообщения из файла
        all_messages = self.load_messages_from_file()
        
        # Фильтруем сообщения для текущего пользователя
        user_messages = []
        for msg in all_messages:
            if (msg.get('candidate') == self.user_data.get('username') or
                msg.get('interviewer') == self.user_data.get('username') or
                msg.get('requested_by') == self.user_data.get('username')):
                user_messages.append(msg)

        # Получаем статистику из файла
        stats = self.get_message_stats()

        self.stats_label.setText(
            f"📨 Всего сообщений: {stats['total']} | "
            f"🔴 Непрочитанных: {stats['unread']} | "
            f"⏳ Ожидают ответа: {stats['pending']}"
        )

        for msg in user_messages:
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
        message_id = message.get('id')
        
        # Загружаем все сообщения из файла
        all_messages = self.load_messages_from_file()
        
        # Обновляем статус прочтения
        updated = False
        for msg in all_messages:
            if msg.get('id') == message_id:
                msg['read'] = True
                msg['read_at'] = datetime.now().isoformat()
                updated = True
                break
        
        if updated:
            # Сохраняем обновленный список
            self.save_messages_to_file(all_messages)
            
            # Обновляем отображение
            self.load_messages()

    def delete_selected(self):
        """Удаляет выбранное сообщение"""
        current = self.messages_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Ошибка", "Выберите сообщение для удаления")
            return

        self.delete_message(current)

    def delete_message(self, item):
        """Удаляет конкретное сообщение из файла"""
        message = item.data(Qt.UserRole)
        message_id = message.get('id')
        
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить это сообщение?\n\n{message.get('message', '')[:100]}...",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Загружаем все сообщения из файла
            all_messages = self.load_messages_from_file()
            
            # Фильтруем, удаляя нужное сообщение
            filtered_messages = [m for m in all_messages if m.get('id') != message_id]
            
            if len(filtered_messages) < len(all_messages):
                # Сохраняем обновленный список
                if self.save_messages_to_file(filtered_messages):
                    # Обновляем отображение
                    self.load_messages()
                    QMessageBox.information(self, "Успех", "Сообщение удалено")
                else:
                    QMessageBox.critical(self, "Ошибка", "Не удалось сохранить изменения")
            else:
                QMessageBox.warning(self, "Ошибка", "Сообщение не найдено в файле")

    def resolve_all_messages(self):
        """Решает все сообщения: прочитывает и автоматически отвечает на запросы"""
        reply = QMessageBox.question(
            self,
            "Решение всех сообщений",
            "Это действие отметит все сообщения как прочитанные и автоматически ответит на все ожидающие запросы переноса, подтверждая их.\n\n"
            "Продолжить?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Загружаем все сообщения
        all_messages = self.load_messages_from_file()
        if not all_messages:
            QMessageBox.information(self, "Информация", "Нет сообщений для обработки")
            return

        # Показываем прогресс бар
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(all_messages))
        self.progress_bar.setValue(0)

        updated_count = 0
        resolved_count = 0
        current_time = datetime.now().isoformat()

        for i, msg in enumerate(all_messages):
            # Обновляем прогресс
            self.progress_bar.setValue(i + 1)
            QApplication.processEvents()

            # Отмечаем как прочитанное
            if not msg.get('read', False):
                msg['read'] = True
                msg['read_at'] = current_time
                updated_count += 1

            # Автоматически отвечаем на ожидающие запросы
            if msg.get('type') == 'reschedule_request' and msg.get('status') == 'pending':
                # Подтверждаем перенос с предложением альтернативы через 2 дня
                interview = msg.get('interview_data', {})
                if interview:
                    new_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
                    new_time = "11:00"
                    
                    # Вызываем метод подтверждения
                    result = self.manager.confirm_reschedule(
                        msg.get('id'),
                        new_date,
                        new_time
                    )
                    
                    if result.get('success'):
                        resolved_count += 1
                        msg['status'] = 'confirmed'
                        msg['resolved_at'] = current_time

        # Сохраняем изменения
        if updated_count > 0 or resolved_count > 0:
            self.save_messages_to_file(all_messages)
            
            QMessageBox.information(
                self,
                "Операция завершена",
                f"✅ Обработано сообщений: {len(all_messages)}\n"
                f"📖 Отмечено как прочитанные: {updated_count}\n"
                f"🔄 Подтверждено запросов на перенос: {resolved_count}"
            )
        else:
            QMessageBox.information(self, "Информация", "Нет сообщений для обработки")

        # Скрываем прогресс бар и обновляем список
        self.progress_bar.setVisible(False)
        self.load_messages()

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
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.confirm_reschedule)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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