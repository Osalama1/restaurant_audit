// Language Switcher Module
const LanguageSwitcher = {
    // Current language
    currentLang: localStorage.getItem('app_language') || 'en',
    
    // Translations object
    translations: {},
    
    // Initialize language system
    init: async function() {
        // Load translations
        await this.loadTranslations();
        
        // Apply saved language
        this.applyLanguage(this.currentLang);
        
        // Add language switcher to UI
        this.addLanguageSwitcher();
        
        // Setup event listeners
        this.setupEventListeners();
    },
    
    // Load translation files
    loadTranslations: async function() {
        try {
            // Load Arabic translations
            const arResponse = await fetch('/api/method/restaurant_audit.api.translation_api.get_translations?lang=ar');
            const arData = await arResponse.json();
            if (arData.success) {
                this.translations.ar = arData.message;
            } else {
                throw new Error(arData.message);
            }
            
            // Load English translations (optional, can use defaults)
            const enResponse = await fetch('/api/method/restaurant_audit.api.translation_api.get_translations?lang=en');
            const enData = await enResponse.json();
            if (enData.success) {
                this.translations.en = enData.message || {};
            } else {
                this.translations.en = {};
            }
        } catch (error) {
            console.error('Error loading translations:', error);
            // Fallback to basic translations
            this.translations.ar = this.getBasicArabicTranslations();
            this.translations.en = {};
        }
    },
    
    // Apply language to the page
    applyLanguage: function(lang) {
        this.currentLang = lang;
        localStorage.setItem('app_language', lang);
        
        // Set HTML attributes
        document.documentElement.lang = lang;
        document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
        
        // Load RTL styles if Arabic
        if (lang === 'ar') {
            this.loadRTLStyles();
            this.loadArabicFont();
        } else {
            this.removeRTLStyles();
        }
        
        // Translate all elements
        this.translatePage();
        
        // Update date/time formats
        this.updateDateTimeFormats();
        
        // Fire custom event
        document.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: lang } }));
    },
    
    // Load RTL stylesheet
    loadRTLStyles: function() {
        if (!document.getElementById('rtl-styles')) {
            const link = document.createElement('link');
            link.id = 'rtl-styles';
            link.rel = 'stylesheet';
            link.href = '/assets/restaurant_audit/css/rtl.css';
            document.head.appendChild(link);
        }
    },
    
    // Load Arabic font
    loadArabicFont: function() {
        if (!document.getElementById('arabic-font')) {
            const link = document.createElement('link');
            link.id = 'arabic-font';
            link.rel = 'stylesheet';
            link.href = 'https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap';
            document.head.appendChild(link);
        }
    },
    
    // Remove RTL styles
    removeRTLStyles: function() {
        const rtlStyles = document.getElementById('rtl-styles');
        if (rtlStyles) {
            rtlStyles.remove();
        }
    },
    
    // Add language switcher to UI
    addLanguageSwitcher: function() {
        // Check if switcher already exists
        if (document.getElementById('language-switcher')) return;
        
        const switcher = document.createElement('div');
        switcher.id = 'language-switcher';
        switcher.className = 'language-switcher';
        switcher.innerHTML = `
            <button class="lang-btn ${this.currentLang === 'en' ? 'active' : ''}" data-lang="en">
                English
            </button>
            <button class="lang-btn ${this.currentLang === 'ar' ? 'active' : ''}" data-lang="ar">
                العربية
            </button>
        `;
        
        // Add to header or appropriate location
        const header = document.querySelector('.header-content');
        if (header) {
            header.appendChild(switcher);
        }
        
        // Add CSS for switcher
        this.addSwitcherStyles();
    },
    
    // Add styles for language switcher
    addSwitcherStyles: function() {
        if (!document.getElementById('language-switcher-styles')) {
            const style = document.createElement('style');
            style.id = 'language-switcher-styles';
            style.textContent = `
                .language-switcher {
                    display: flex;
                    gap: 0.5rem;
                    margin-left: 1rem;
                }
                
                [dir="rtl"] .language-switcher {
                    margin-left: 0;
                    margin-right: 1rem;
                }
                
                .lang-btn {
                    padding: 0.5rem 1rem;
                    border: 1px solid var(--neutral-300);
                    background: var(--white);
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 0.875rem;
                    transition: all 0.3s ease;
                }
                
                .lang-btn:hover {
                    background: var(--neutral-100);
                }
                
                .lang-btn.active {
                    background: var(--primary-color);
                    color: var(--white);
                    border-color: var(--primary-color);
                }
            `;
            document.head.appendChild(style);
        }
    },
    
    // Setup event listeners
    setupEventListeners: function() {
        // Language switcher buttons
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('lang-btn')) {
                const lang = e.target.dataset.lang;
                this.applyLanguage(lang);
                
                // Update active state
                document.querySelectorAll('.lang-btn').forEach(btn => {
                    btn.classList.toggle('active', btn.dataset.lang === lang);
                });
            }
        });
    },
    
    // Translate the page
    translatePage: function() {
        // Translate elements with data-translate attribute
        document.querySelectorAll('[data-translate]').forEach(element => {
            const key = element.dataset.translate;
            const translation = this.translate(key);
            if (translation) {
                if (element.placeholder !== undefined) {
                    element.placeholder = translation;
                } else {
                    element.textContent = translation;
                }
            }
        });
        
        // Translate specific elements by ID
        this.translateById();
        
        // Translate form labels
        this.translateFormLabels();
        
        // Translate buttons
        this.translateButtons();
    },
    
    // Get translation for a key
    translate: function(key) {
        if (this.currentLang === 'en') {
            return key; // Return key as is for English (or use English translations if loaded)
        }
        return this.translations[this.currentLang]?.[key] || key;
    },
    
    // Translate elements by ID
    translateById: function() {
        const idTranslations = {
            'restaurant-name': 'Restaurant Name',
            'user-name': 'User Name',
            'loading': 'Loading',
            'error': 'Error',
            'submit-btn': 'Submit',
            'save-progress-btn': 'Save Progress',
            'logout-btn': 'Logout',
            'back-btn': 'Back'
        };
        
        Object.entries(idTranslations).forEach(([id, key]) => {
            const element = document.getElementById(id);
            if (element) {
                const translation = this.translate(key);
                if (element.tagName === 'BUTTON') {
                    element.textContent = translation;
                } else if (element.tagName === 'INPUT') {
                    element.placeholder = translation;
                } else {
                    element.textContent = translation;
                }
            }
        });
    },
    
    // Translate form labels
    translateFormLabels: function() {
        document.querySelectorAll('label').forEach(label => {
            const text = label.textContent.trim();
            const translation = this.translate(text);
            if (translation !== text) {
                label.textContent = translation;
            }
        });
    },
    
    // Translate buttons
    translateButtons: function() {
        document.querySelectorAll('button').forEach(button => {
            if (!button.dataset.noTranslate) {
                const text = button.textContent.trim();
                const translation = this.translate(text);
                if (translation !== text) {
                    button.textContent = translation;
                }
            }
        });
    },
    
    // Update date/time formats based on language
    updateDateTimeFormats: function() {
        const locale = this.currentLang === 'ar' ? 'ar-SA' : 'en-US';
        
        // Update all date displays
        document.querySelectorAll('[data-date]').forEach(element => {
            const dateStr = element.dataset.date;
            if (dateStr) {
                const date = new Date(dateStr);
                element.textContent = date.toLocaleDateString(locale);
            }
        });
        
        // Update all time displays
        document.querySelectorAll('[data-time]').forEach(element => {
            const timeStr = element.dataset.time;
            if (timeStr) {
                const time = new Date(timeStr);
                element.textContent = time.toLocaleTimeString(locale);
            }
        });
    },
    
    // Get basic Arabic translations (fallback)
    getBasicArabicTranslations: function() {
        return {
            'Loading': 'جاري التحميل',
            'Submit': 'إرسال',
            'Cancel': 'إلغاء',
            'Save': 'حفظ',
            'Back': 'رجوع',
            'Logout': 'تسجيل الخروج',
            'Restaurant': 'مطعم',
            'Audit': 'تدقيق',
            'Yes': 'نعم',
            'No': 'لا',
            'Completed': 'مكتمل',
            'Pending': 'قيد الانتظار',
            'Active': 'نشط',
            'Search': 'بحث',
            'Filter': 'تصفية',
            'Dashboard': 'لوحة التحكم',
            'Settings': 'الإعدادات',
            'Error': 'خطأ',
            'Success': 'نجاح',
            'Warning': 'تحذير'
        };
    },
    
    // Format number based on language
    formatNumber: function(number) {
        const locale = this.currentLang === 'ar' ? 'ar-SA' : 'en-US';
        return new Intl.NumberFormat(locale).format(number);
    },
    
    // Format currency based on language
    formatCurrency: function(amount, currency = 'SAR') {
        const locale = this.currentLang === 'ar' ? 'ar-SA' : 'en-US';
        return new Intl.NumberFormat(locale, {
            style: 'currency',
            currency: currency
        }).format(amount);
    }
    
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    LanguageSwitcher.init();
});

// Export for use in other modules
window.LanguageSwitcher = LanguageSwitcher;