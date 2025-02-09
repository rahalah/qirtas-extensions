from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QComboBox, 
                           QLabel, QPushButton, QMessageBox,
                           QApplication, QTextEdit, QSpinBox, QCheckBox, QTabWidget, QWidget, QProgressDialog)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QTextCursor
from deep_translator import GoogleTranslator
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
import nltk

class TranslationThread(QThread):
    translation_done = pyqtSignal(str, str)  # إشارة عند انتهاء الترجمة

    def __init__(self, translator, text):
        super().__init__()
        self.translator = translator
        self.text = text

    def run(self):
        try:
            translated_text = self.translator.translate_text(self.text)
            self.translation_done.emit(self.text, translated_text)
        except Exception as e:
            self.translation_done.emit(self.text, f"خطأ في الترجمة: {str(e)}")

class TranslatorSettings(QDialog):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings or {}
        self.setWindowTitle("إعدادات الترجمة")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # إنشاء تبويبات للإعدادات
        tab_widget = QTabWidget()
        
        # تبويب الإعدادات الأساسية
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)
        
        # اللغات
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("اللغة المصدر:"))
        self.source_combo = QComboBox()
        self.source_combo.addItems(self.get_supported_languages())
        source_layout.addWidget(self.source_combo)
        basic_layout.addLayout(source_layout)
        
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("اللغة الهدف:"))
        self.target_combo = QComboBox()
        self.target_combo.addItems(self.get_supported_languages())
        target_layout.addWidget(self.target_combo)
        basic_layout.addLayout(target_layout)
        
        tab_widget.addTab(basic_tab, "إعدادات أساسية")
        
        # تبويب الإعدادات المتقدمة
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)
        
        # عدد الخيوط
        threads_layout = QHBoxLayout()
        threads_layout.addWidget(QLabel("عدد الخيوط المتوازية:"))
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 10)
        self.threads_spin.setValue(self.settings.get('max_threads', 4))
        threads_layout.addWidget(self.threads_spin)
        advanced_layout.addLayout(threads_layout)
        
        # حجم النص الأقصى
        chunk_layout = QHBoxLayout()
        chunk_layout.addWidget(QLabel("الحد الأقصى لحجم النص (حرف):"))
        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(100, 5000)
        self.chunk_spin.setValue(self.settings.get('max_chunk_size', 1000))
        chunk_layout.addWidget(self.chunk_spin)
        advanced_layout.addLayout(chunk_layout)
        

        
        tab_widget.addTab(advanced_tab, "إعدادات متقدمة")
        
        layout.addWidget(tab_widget)
        
        # أزرار
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("حفظ")
        save_btn.clicked.connect(self.save_settings)
        test_btn = QPushButton("اختبار الترجمة")
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        
        # تحميل الإعدادات الحالية
        self.load_current_settings()
        
    def get_supported_languages(self):
        """الحصول على قائمة اللغات المدعومة"""
        return ['auto', 'ar', 'en', 'fr', 'es', 'de', 'it', 'ru', 'zh', 'ja', 'ko', 
                'hi', 'ur', 'fa', 'tr', 'id', 'th', 'vi', 'ms']
        
    def load_current_settings(self):
        """تحميل الإعدادات الحالية"""
        self.source_combo.setCurrentText(self.settings.get('source_lang', 'auto'))
        self.target_combo.setCurrentText(self.settings.get('target_lang', 'en'))
        
    def save_settings(self):
        """حفظ الإعدادات"""
        self.settings.update({
            'source_lang': self.source_combo.currentText(),
            'target_lang': self.target_combo.currentText(),
            'max_threads': self.threads_spin.value(),
            'max_chunk_size': self.chunk_spin.value(),
        })
        self.accept()

class Translator:
    def __init__(self):
        self.settings = self.load_settings()
        self.translator = GoogleTranslator(
            source=self.settings.get('source_lang', 'auto'),
            target=self.settings.get('target_lang', 'en')
        )
        max_threads = self.settings.get('max_threads', 4)  # القيمة الافتراضية 4
        self.executor = ThreadPoolExecutor(max_workers=max_threads)
        self.translation_cache = {}

    def load_settings(self):
        settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'source_lang': 'auto',
            'target_lang': 'en',
            'max_threads': 4,  # إضافة القيمة الافتراضية
            'max_chunk_size': 1000,  # إضافة القيمة الافتراضية
        }
        
    def save_settings(self):
        settings_path = os.path.join(os.path.dirname(__file__), 'settings.json')
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=4)
            
    def translate_chunk(self, chunk):
        """ترجمة جزء من النص مع استخدام التخزين المؤقت"""
        if chunk in self.translation_cache:
            return self.translation_cache[chunk]
        
        try:
            translated_text = self.translator.translate(chunk)
            self.translation_cache[chunk] = translated_text
            return translated_text
        except Exception as e:
            return f"خطأ في ترجمة الجزء: {str(e)}"
            
    def translate_text(self, text):
        """ترجمة النص مع دعم التقسيم والترجمة المتوازية والحفاظ على تنسيق الأسطر"""
        try:
            lines = text.splitlines()
            final_result = []
            
            for line in lines:
                if not line.strip():
                    final_result.append('')
                    continue
                
                max_chunk_size = self.settings.get('max_chunk_size', 1000)
                chunks = self.split_text_into_chunks(line, max_chunk_size)
                
                translated_chunks = list(self.executor.map(self.translate_chunk, chunks))
                
                final_result.append(' '.join(translated_chunks))
            
            return '\n'.join(final_result)
            
        except Exception as e:
            raise Exception(f"فشل في الترجمة: {str(e)}\nالرجاء التحقق من اتصال الإنترنت وإعدادات الترجمة.")
            

    def split_text_into_chunks(self, text, max_size):
        """
        تقسيم النص إلى أجزاء مع الحفاظ على تماسك الجمل
        """
        chunks = []
        current_chunk = []
        current_size = 0

        # تقسيم النص إلى جمل
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())

        for sentence in sentences:
            # تجاهل الجمل الفارغة
            if not sentence.strip():
                continue
                
            # إذا كانت الجملة أكبر من الحجم الأقصى
            if len(sentence) > max_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                # تقسيم الجملة الطويلة مع الحفاظ على الكلمات كاملة
                words = sentence.split()
                temp_chunk = []
                temp_size = 0
                for word in words:
                    if temp_size + len(word) + 1 > max_size:
                        if temp_chunk:
                            chunks.append(' '.join(temp_chunk))
                        temp_chunk = [word]
                        temp_size = len(word)
                    else:
                        temp_chunk.append(word)
                        temp_size += len(word) + 1
                if temp_chunk:
                    chunks.append(' '.join(temp_chunk))
            else:
                # إضافة الجملة للجزء الحالي أو إنشاء جزء جديد
                if current_size + len(sentence) + 1 > max_size:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = [sentence]
                    current_size = len(sentence)
                else:
                    current_chunk.append(sentence)
                    current_size += len(sentence) + 1

        # إضافة الجزء الأخير
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def improve_cache(self):
        # تحديد حجم أقصى للتخزين المؤقت
        MAX_CACHE_SIZE = 1000
        
        if len(self.translation_cache) > MAX_CACHE_SIZE:
            # حذف أقدم الترجمات عند تجاوز الحد
            oldest_entries = list(self.translation_cache.items())[:100]
            for key, _ in oldest_entries:
                del self.translation_cache[key]

    def optimize_text_processing(self, text):
        # تجنب تقسيم الجمل المترابطة
        sentences = nltk.sent_tokenize(text)
        
        optimized_chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            if current_size + len(sentence) > self.settings.get('max_chunk_size', 1000):
                optimized_chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = len(sentence)
            else:
                current_chunk.append(sentence)
                current_size += len(sentence)
        
        if current_chunk:
            optimized_chunks.append(' '.join(current_chunk))
        
        return optimized_chunks

class Extension:
    def __init__(self, editor):
        self.editor = editor
        self.translator = Translator()
        self.original_text = ""
        self.original_cursor = None
        self.last_text = ""  # لتخزين آخر نص تم ترجمته
    

    def get_menu_items(self):
        """إضافة عناصر القائمة الرئيسية"""
        return [{
            'name': 'إعدادات الترجمة',
            'callback': self.show_settings
        }]
        
    def get_context_menu_items(self):
        """إضافة عناصر القائمة المنبثقة"""
        return [{
            'name': 'ترجمة النص المحدد',
            'callback': self.translate_selected,
            'shortcut': 'Ctrl+T'
        }]
        
    def get_shortcuts(self):
        """تعريف اختصارات الملحق"""
        return [{
            'shortcut': 'Ctrl+T',  # تغيير الاختصار لتجنب التعارض
            'callback': self.translate_selected
        }]
        
    def show_settings(self):
        """عرض نافذة الإعدادات"""
        dialog = TranslatorSettings(self.editor, self.translator.settings)
        dialog.exec_()

            
    def translate_selected(self):
        """ترجمة النص المحدد"""
        current_editor = self.editor.get_current_editor()
        if not current_editor:
            return

        cursor = current_editor.textCursor()
        selected_text = cursor.selectedText()

        if not selected_text:
            QMessageBox.warning(self.editor, "تنبيه", "الرجاء تحديد النص المراد ترجمته")
            return

        # حفظ النص الأصلي وموضعه
        self.original_text = selected_text
        self.original_cursor = QTextCursor(cursor)  # نسخة من المؤشر الأصلي

        # استخدام خيط للترجمة
        self.translation_thread = TranslationThread(self.translator, selected_text)
        self.translation_thread.translation_done.connect(self.show_translation_popup)
        self.translation_thread.start()

    def show_translation_popup(self, original_text, translated_text):
        """عرض القائمة المنبثقة للترجمة"""
        menu = QDialog(self.editor)
        menu.setWindowTitle("الترجمة")
        layout = QVBoxLayout(menu)
        
        # إضافة مربعات نص قابلة للتحرير
        layout.addWidget(QLabel("النص الأصلي:"))
        original_text_edit = QTextEdit()
        original_text_edit.setPlainText(original_text)
        original_text_edit.setReadOnly(True)  # جعل النص الأصلي للقراءة فقط
        layout.addWidget(original_text_edit)

        layout.addWidget(QLabel("الترجمة:"))
        translated_text_edit = QTextEdit()
        translated_text_edit.setPlainText(translated_text)
        layout.addWidget(translated_text_edit)

        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        
        # زر نسخ الترجمة
        copy_btn = QPushButton("نسخ الترجمة")
        copy_btn.clicked.connect(lambda: self.copy_to_clipboard(translated_text_edit.toPlainText()))
        buttons_layout.addWidget(copy_btn)

        # زر استبدال النص
        replace_btn = QPushButton("استبدال بالترجمة")
        replace_btn.clicked.connect(lambda: self.replace_text(translated_text_edit.toPlainText()))
        buttons_layout.addWidget(replace_btn)

        # زر إلغاء
        cancel_btn = QPushButton("إلغاء")
        cancel_btn.clicked.connect(menu.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)
        menu.setLayout(layout)
        menu.resize(500, 400)  # تعيين حجم النافذة
        menu.exec_()

    def copy_to_clipboard(self, text):
        """نسخ النص إلى الحافظة"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self.editor, "تم", "تم نسخ النص إلى الحافظة")

    def replace_text(self, new_text):
        """استبدال النص المحدد بالترجمة"""
        if not self.original_cursor:
            QMessageBox.warning(self.editor, "خطأ", "لم يتم العثور على النص الأصلي")
            return

        current_editor = self.editor.get_current_editor()
        if not current_editor:
            return

        # استخدام المؤشر الأصلي للاستبدال
        cursor = self.original_cursor
        cursor.beginEditBlock()
        
        # تحديد النص الأصلي
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        
        # استبدال النص
        cursor.removeSelectedText()
        cursor.insertText(new_text)
        cursor.endEditBlock()

        # إعادة تعيين المتغيرات
        self.original_text = ""
        self.original_cursor = None
