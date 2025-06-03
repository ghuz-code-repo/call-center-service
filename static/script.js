// static/script.js
document.addEventListener('DOMContentLoaded', () => {
    const scriptSelect = document.getElementById('script-select');
    const scriptContainer = document.getElementById('script-container');
    const stepContent = document.getElementById('step-content');
    const optionsContainer = document.getElementById('options-container');
    const backButton = document.getElementById('back-button');
    const messageBox = document.getElementById('message-box');
    const finalStepActions = document.getElementById('final-step-actions'); // Новый элемент
    const startNewScriptButton = document.getElementById('start-new-script-button'); // Новый элемент

    let currentScriptId = null;
    let currentStepId = null;
    let history = []; // История шагов для кнопки "Назад"

    /**
     * Отображает временное сообщение пользователю.
     * @param {string} message - Текст сообщения.
     * @param {string} type - Тип сообщения (например, 'success', 'error', 'info').
     */
    function showMessage(message, type = 'info') {
        messageBox.textContent = message;
        messageBox.className = `fixed bottom-4 right-4 px-4 py-2 rounded-md shadow-lg transition-opacity duration-300 ${type === 'success' ? 'bg-green-500' : type === 'error' ? 'bg-red-500' : 'bg-blue-500'} text-white`;
        messageBox.classList.remove('hidden');
        setTimeout(() => {
            messageBox.classList.add('hidden');
        }, 3000);
    }

    /**
     * Загружает и отображает данные шага скрипта.
     * @param {string} scriptId - ID скрипта.
     * @param {string} stepId - ID шага.
     * @param {boolean} addToHistory - Добавлять ли текущий шаг в историю (true для обычного перехода, false для загрузки из истории).
     */
    async function loadStep(scriptId, stepId, addToHistory = true) {
        if (!scriptId || !stepId) {
            console.error("Не указан ID скрипта или шага.");
            return;
        }

        if (addToHistory && currentStepId && currentScriptId === scriptId) {
            history.push(currentStepId);
        }
        currentScriptId = scriptId;
        currentStepId = stepId;

        try {
            const response = await fetch(`/api/get_step/${scriptId}/${stepId}`);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Ошибка при загрузке шага');
            }
            const stepData = await response.json();

            stepContent.innerHTML = stepData.text;
            optionsContainer.innerHTML = ''; // Очищаем предыдущие опции
            finalStepActions.style.display = 'none'; // Скрываем действия для финального шага по умолчанию

            if (stepData.is_final) { // Если это финальный шаг
                optionsContainer.style.display = 'none'; // Скрываем опции
                finalStepActions.style.display = 'block'; // Показываем действия для финального шага
                backButton.style.display = 'none'; // Скрываем кнопку "Назад" на финальном шаге
                showMessage("Скрипт завершен.", 'info');
            } else {
                if (stepData.options && stepData.options.length > 0) {
                    stepData.options.forEach(option => {
                        const button = document.createElement('button');
                        button.className = 'w-full bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded-lg shadow-md transition duration-300 ease-in-out transform hover:scale-105';
                        button.textContent = option.text;
                        button.dataset.nextStep = option.next_step;
                        button.addEventListener('click', handleOptionClick);
                        optionsContainer.appendChild(button);
                    });
                    optionsContainer.style.display = 'block'; // Показываем контейнер с опциями
                } else {
                    // Если нет опций, но это не финальный шаг (возможно, ошибка конфигурации)
                    optionsContainer.style.display = 'none';
                    showMessage("У этого шага нет опций, и он не помечен как финальный.", 'warning');
                }
                backButton.style.display = history.length > 0 ? 'block' : 'none';
            }

            scriptContainer.classList.remove('hidden'); // Показываем контейнер скрипта
        } catch (error) {
            console.error('Ошибка при загрузке шага:', error);
            stepContent.innerHTML = `<p class="text-red-600">Ошибка: ${error.message}. Пожалуйста, выберите другой скрипт или шаг.</p>`;
            optionsContainer.innerHTML = '';
            backButton.style.display = 'none';
            finalStepActions.style.display = 'none';
            showMessage(`Ошибка: ${error.message}`, 'error');
        }
    }

    /**
     * Обработчик клика по кнопке опции.
     * Переходит к следующему шагу.
     * @param {Event} event - Событие клика.
     */
    function handleOptionClick(event) {
        const nextStepId = event.target.dataset.nextStep;
        if (nextStepId) {
            loadStep(currentScriptId, nextStepId);
        } else {
            showMessage("Не указан следующий шаг для этой опции.", 'error');
        }
    }

    /**
     * Обработчик изменения выбора скрипта.
     * Загружает начальный шаг выбранного скрипта.
     */
    scriptSelect.addEventListener('change', () => {
        const selectedScriptId = scriptSelect.value;
        if (selectedScriptId) {
            history = []; // Очищаем историю при смене скрипта
            loadStep(selectedScriptId, 'start'); // Все скрипты начинаются с шага 'start'
        } else {
            scriptContainer.classList.add('hidden'); // Скрываем контейнер, если скрипт не выбран
            stepContent.innerHTML = '';
            optionsContainer.innerHTML = '';
            backButton.style.display = 'none';
            finalStepActions.style.display = 'none';
            currentScriptId = null;
            currentStepId = null;
        }
    });

    /**
     * Обработчик клика по кнопке "Назад".
     * Возвращает к предыдущему шагу в истории.
     */
    backButton.addEventListener('click', () => {
        if (history.length > 0) {
            const prevStepId = history.pop();
            loadStep(currentScriptId, prevStepId, false); // Не добавляем в историю, так как это возврат
        }
    });

    /**
     * Обработчик для кнопки "Начать новый скрипт".
     * Перезагружает страницу для сброса интерфейса.
     */
    startNewScriptButton.addEventListener('click', () => {
        window.location.reload(); // Простейший способ сбросить интерфейс оператора
    });
});
