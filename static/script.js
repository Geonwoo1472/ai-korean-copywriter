document.addEventListener('DOMContentLoaded', () => {
    // Marked.js 보안 설정
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true,
        });
    }

    const generateBtn = document.getElementById('generateBtn');
    const stopBtn = document.getElementById('stopBtn');
    const resultCard = document.getElementById('resultCard');
    const resultContent = document.getElementById('resultContent');
    const resultHeader = document.getElementById('resultHeader');
    const copyBtn = document.getElementById('copyBtn');

    // Progress elements
    const progressContainer = document.getElementById('progressContainer');
    const progressFill = document.getElementById('progressFill');
    const progressStage = document.getElementById('progressStage');
    const progressPercent = document.getElementById('progressPercent');
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');

    // Abort controller for canceling requests
    let currentAbortController = null;

    // ═══════════════════════════════════════
    // Theme Manager
    // ═══════════════════════════════════════
    const themeToggle = document.getElementById('themeToggle');
    const themeButtons = themeToggle.querySelectorAll('.theme-btn');
    const htmlEl = document.documentElement;

    function applyTheme(setting) {
        // setting: 'light', 'dark', 'auto'
        let resolvedTheme;
        if (setting === 'auto') {
            resolvedTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        } else {
            resolvedTheme = setting;
        }

        htmlEl.setAttribute('data-theme', resolvedTheme);
        htmlEl.setAttribute('data-theme-setting', setting);
        localStorage.setItem('theme', setting);

        // Update meta theme-color
        const metaTheme = document.querySelector('meta[name="theme-color"]');
        if (metaTheme) {
            metaTheme.setAttribute('content', resolvedTheme === 'dark' ? '#0f172a' : '#6366f1');
        }

        // Update active button
        themeButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.themeValue === setting);
        });
    }

    // Init theme from stored setting
    const savedSetting = htmlEl.getAttribute('data-theme-setting') || localStorage.getItem('theme') || 'auto';
    applyTheme(savedSetting);

    // Theme button clicks
    themeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            applyTheme(btn.dataset.themeValue);
        });
    });

    // Listen for system theme changes (for auto mode)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        const current = htmlEl.getAttribute('data-theme-setting');
        if (current === 'auto') {
            applyTheme('auto');
        }
    });

    // ═══════════════════════════════════════
    // Check Active LLM Status
    // ═══════════════════════════════════════
    const checkLLMStatus = async () => {
        const activeEngineBadge = document.getElementById('activeEngineBadge');
        if (!activeEngineBadge) return;
        
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            const text = activeEngineBadge.querySelector('.status-text');
            activeEngineBadge.className = 'active-engine-badge';
            
            if (data.provider === 'gemini') {
                activeEngineBadge.classList.add('active-gemini');
                text.innerText = `AI 엔진: Gemini (${data.model})`;
            } else if (data.provider === 'openai') {
                activeEngineBadge.classList.add('active-openai');
                text.innerText = `AI 엔진: OpenAI (${data.model})`;
            } else if (data.provider === 'custom') {
                activeEngineBadge.classList.add('active-custom');
                text.innerText = `AI 엔진: Custom (${data.model})`;
            } else {
                activeEngineBadge.classList.add('active-mock');
                text.innerText = 'AI 엔진: 데모 모드 (Mock 데이터)';
            }
            
            activeEngineBadge.classList.add('visible');
        } catch (error) {
            console.error('Failed to fetch AI status:', error);
            const text = activeEngineBadge.querySelector('.status-text');
            activeEngineBadge.className = 'active-engine-badge active-mock visible';
            text.innerText = 'AI 엔진: 상태 확인 실패';
        }
    };

    checkLLMStatus();

    // ═══════════════════════════════════════
    // Engine Sub Settings Toggle
    // ═══════════════════════════════════════
    // ═══════════════════════════════════════
    // Engine Sub Settings & API Keys & Badge Sync
    // ═══════════════════════════════════════
    const engineSelect = document.getElementById('engine');
    const geminiSettings = document.getElementById('geminiSettings');
    const openaiSettings = document.getElementById('openaiSettings');
    const localSettings = document.getElementById('localSettings');
    const customSettings = document.getElementById('customSettings');
    const geminiModelSelect = document.getElementById('geminiModel');
    const openaiModelSelect = document.getElementById('openaiModel');
    const localModelInput = document.getElementById('localModel');
    const customModelInput = document.getElementById('customModel');
    const customBaseUrlInput = document.getElementById('customBaseUrl');
    
    // API Keys inputs
    const geminiApiKeyInput = document.getElementById('geminiApiKey');
    const openaiApiKeyInput = document.getElementById('openaiApiKey');
    const customApiKeyInput = document.getElementById('customApiKey');

    // Load API Keys and settings from LocalStorage
    if (geminiApiKeyInput) {
        geminiApiKeyInput.value = localStorage.getItem('gemini_api_key') || '';
        geminiApiKeyInput.addEventListener('input', () => {
            localStorage.setItem('gemini_api_key', geminiApiKeyInput.value);
        });
    }
    if (openaiApiKeyInput) {
        openaiApiKeyInput.value = localStorage.getItem('openai_api_key') || '';
        openaiApiKeyInput.addEventListener('input', () => {
            localStorage.setItem('openai_api_key', openaiApiKeyInput.value);
        });
    }
    if (customApiKeyInput) {
        customApiKeyInput.value = localStorage.getItem('custom_api_key') || '';
        customApiKeyInput.addEventListener('input', () => {
            localStorage.setItem('custom_api_key', customApiKeyInput.value);
        });
    }
    if (customModelInput) {
        customModelInput.value = localStorage.getItem('custom_model') !== null ? localStorage.getItem('custom_model') : 'llama-3.3-70b-versatile';
        customModelInput.addEventListener('input', () => {
            localStorage.setItem('custom_model', customModelInput.value);
        });
    }
    if (customBaseUrlInput) {
        customBaseUrlInput.value = localStorage.getItem('custom_base_url') !== null ? localStorage.getItem('custom_base_url') : 'https://api.groq.com/openai/v1';
        customBaseUrlInput.addEventListener('input', () => {
            localStorage.setItem('custom_base_url', customBaseUrlInput.value);
        });
    }

    const activeEngineBadge = document.getElementById('activeEngineBadge');
    const updateBadgeFromUI = () => {
        if (!activeEngineBadge) return;
        const engine = engineSelect.value;
        const text = activeEngineBadge.querySelector('.status-text');
        
        activeEngineBadge.className = 'active-engine-badge';
        
        if (engine === 'auto') {
            checkLLMStatus(); // auto일 때는 서버 감지 상태를 갱신
        } else if (engine === 'gemini') {
            const model = geminiModelSelect.value;
            activeEngineBadge.classList.add('active-gemini');
            text.innerText = `AI 엔진: Gemini (${model})`;
            activeEngineBadge.classList.add('visible');
        } else if (engine === 'openai') {
            const model = openaiModelSelect.value;
            activeEngineBadge.classList.add('active-openai');
            text.innerText = `AI 엔진: OpenAI (${model})`;
            activeEngineBadge.classList.add('visible');
        } else if (engine === 'local') {
            const model = localModelInput.value.trim() || 'gemma2:2b';
            activeEngineBadge.classList.add('active-custom');
            text.innerText = `AI 엔진: 로컬 (${model})`;
            activeEngineBadge.classList.add('visible');
        } else if (engine === 'custom') {
            const model = customModelInput.value.trim() || 'custom-model';
            activeEngineBadge.classList.add('active-custom');
            text.innerText = `AI 엔진: Custom (${model})`;
            activeEngineBadge.classList.add('visible');
        }
    };
    
    engineSelect.addEventListener('change', () => {
        geminiSettings.style.display = 'none';
        openaiSettings.style.display = 'none';
        localSettings.style.display = 'none';
        customSettings.style.display = 'none';
        geminiSettings.classList.remove('visible');
        openaiSettings.classList.remove('visible');
        localSettings.classList.remove('visible');
        customSettings.classList.remove('visible');
        
        if (engineSelect.value === 'gemini') {
            geminiSettings.style.display = 'block';
            geminiSettings.classList.add('visible');
        } else if (engineSelect.value === 'openai') {
            openaiSettings.style.display = 'block';
            openaiSettings.classList.add('visible');
        } else if (engineSelect.value === 'local') {
            localSettings.style.display = 'block';
            localSettings.classList.add('visible');
            checkOllamaStatus();
        } else if (engineSelect.value === 'custom') {
            customSettings.style.display = 'block';
            customSettings.classList.add('visible');
        }
        
        updateBadgeFromUI();
    });

    geminiModelSelect.addEventListener('change', updateBadgeFromUI);
    openaiModelSelect.addEventListener('change', updateBadgeFromUI);
    localModelInput.addEventListener('input', updateBadgeFromUI);
    customModelInput.addEventListener('input', updateBadgeFromUI);

    // Preset Buttons Logic
    const presetButtons = document.querySelectorAll('.btn-preset');
    
    function updateActivePresetButton() {
        if (!presetButtons.length) return;
        const baseUrl = customBaseUrlInput.value.trim();
        const model = customModelInput.value.trim();
        
        presetButtons.forEach(btn => btn.classList.remove('active'));
        
        if (baseUrl === 'https://api.groq.com/openai/v1' && model === 'llama-3.3-70b-versatile') {
            document.getElementById('presetGroq').classList.add('active');
        } else if (baseUrl === 'https://api.deepseek.com/v1' && model === 'deepseek-chat') {
            document.getElementById('presetDeepSeek').classList.add('active');
        } else {
            document.getElementById('presetDirect').classList.add('active');
        }
    }
    
    presetButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const presetType = btn.dataset.preset;
            
            if (presetType === 'groq') {
                customModelInput.value = 'llama-3.3-70b-versatile';
                customBaseUrlInput.value = 'https://api.groq.com/openai/v1';
            } else if (presetType === 'deepseek') {
                customModelInput.value = 'deepseek-chat';
                customBaseUrlInput.value = 'https://api.deepseek.com/v1';
            }
            
            // Dispatch input events to save to local storage & update UI
            customModelInput.dispatchEvent(new Event('input'));
            customBaseUrlInput.dispatchEvent(new Event('input'));
            
            updateActivePresetButton();
            updateBadgeFromUI();
        });
    });

    if (customModelInput) {
        customModelInput.addEventListener('input', updateActivePresetButton);
    }
    if (customBaseUrlInput) {
        customBaseUrlInput.addEventListener('input', updateActivePresetButton);
    }
    
    // Initial active preset selection
    updateActivePresetButton();

    // ═══════════════════════════════════════
    // Ollama Auto Setup System
    // ═══════════════════════════════════════
    const ollamaDot = document.getElementById('ollamaDot');
    const ollamaStatusText = document.getElementById('ollamaStatusText');
    const ollamaRefreshBtn = document.getElementById('ollamaRefreshBtn');
    const localModelList = document.getElementById('localModelList');

    const checkOllamaStatus = async () => {
        ollamaStatusText.innerText = 'Ollama 연결 상태 확인 중...';
        ollamaDot.className = 'ollama-dot checking';
        
        try {
            const response = await fetch('/api/ollama/status');
            const data = await response.json();
            
            if (data.running) {
                ollamaDot.className = 'ollama-dot connected';
                const modelCount = data.models.length;
                ollamaStatusText.innerText = `✅ Ollama 연결됨 · 설치된 모델: ${modelCount}개`;
                
                // Populate datalist with detected models
                if (modelCount > 0) {
                    localModelList.innerHTML = '';
                    data.models.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model.name;
                        option.textContent = `${model.name} (${model.size})`;
                        localModelList.appendChild(option);
                    });
                    // Auto-select first model if current value is default
                    if (localModelInput.value === 'gemma2:2b' || !localModelInput.value) {
                        localModelInput.value = data.models[0].name;
                    }
                }

                // Mark installed models on install buttons
                document.querySelectorAll('.install-model-btn').forEach(btn => {
                    const modelName = btn.dataset.model;
                    const isInstalled = data.models.some(m => 
                        m.name === modelName || m.name.startsWith(modelName.split(':')[0])
                    );
                    if (isInstalled) {
                        btn.classList.add('installed');
                        btn.querySelector('.model-meta').textContent = '✅ 설치 완료';
                    } else {
                        btn.classList.remove('installed');
                        btn.querySelector('.model-meta').textContent = btn.dataset.size;
                    }
                });
            } else {
                ollamaDot.className = 'ollama-dot disconnected';
                ollamaStatusText.innerText = '❌ Ollama가 실행 중이 아닙니다';
            }
        } catch (error) {
            ollamaDot.className = 'ollama-dot disconnected';
            ollamaStatusText.innerText = '❌ Ollama 연결 실패 (서버 확인 필요)';
        }
    };

    ollamaRefreshBtn.addEventListener('click', checkOllamaStatus);

    // Model Pull (One-click install)
    document.querySelectorAll('.install-model-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            if (btn.classList.contains('installed') || btn.classList.contains('pulling')) return;

            const modelName = btn.dataset.model;
            const pullContainer = document.getElementById('pullProgressContainer');
            const pullModelName = document.getElementById('pullModelName');
            const pullPercentEl = document.getElementById('pullPercent');
            const pullProgressFill = document.getElementById('pullProgressFill');
            const pullStatus = document.getElementById('pullStatus');

            btn.classList.add('pulling');
            btn.querySelector('.model-meta').textContent = '다운로드 중...';

            pullContainer.style.display = 'block';
            pullModelName.textContent = `${modelName} 다운로드 중...`;
            pullPercentEl.textContent = '0%';
            pullProgressFill.style.width = '0%';
            pullStatus.textContent = '모델 레이어 다운로드 준비 중...';

            try {
                const response = await fetch('/api/ollama/pull', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model: modelName })
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (!line.startsWith('data: ')) continue;
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.status === 'error') {
                                pullStatus.textContent = `에러: ${data.message}`;
                                btn.classList.remove('pulling');
                                btn.querySelector('.model-meta').textContent = btn.dataset.size;
                                return;
                            }
                            if (data.status === 'success') {
                                pullProgressFill.style.width = '100%';
                                pullPercentEl.textContent = '100%';
                                pullStatus.textContent = '✅ 설치 완료!';
                                btn.classList.remove('pulling');
                                btn.classList.add('installed');
                                btn.querySelector('.model-meta').textContent = '✅ 설치 완료';
                                // Set as current model
                                localModelInput.value = modelName;
                                setTimeout(() => {
                                    pullContainer.style.display = 'none';
                                    checkOllamaStatus();
                                }, 2000);
                                return;
                            }
                            pullStatus.textContent = data.status;
                            if (data.percent > 0) {
                                pullProgressFill.style.width = `${data.percent}%`;
                                pullPercentEl.textContent = `${data.percent}%`;
                            }
                        } catch (e) { /* ignore parse errors */ }
                    }
                }
            } catch (error) {
                pullStatus.textContent = `네트워크 에러: Ollama가 실행 중인지 확인하세요.`;
                btn.classList.remove('pulling');
                btn.querySelector('.model-meta').textContent = btn.dataset.size;
            }
        });
    });

    // ═══════════════════════════════════════
    // Progress Bar Helpers
    // ═══════════════════════════════════════
    function updateProgress(percent, stageText) {
        progressFill.style.width = `${percent}%`;
        progressPercent.textContent = `${percent}%`;
        if (stageText) progressStage.textContent = stageText;

        step1.className = 'step';
        step2.className = 'step';
        step3.className = 'step';

        if (percent >= 0) step1.classList.add('active');
        if (percent >= 15) { step1.classList.add('done'); step2.classList.add('active'); }
        if (percent >= 90) { step2.classList.add('done'); step3.classList.add('active'); }
        if (percent >= 100) step3.classList.add('done');
    }

    function resetProgress() {
        progressFill.style.width = '0%';
        progressPercent.textContent = '0%';
        progressStage.textContent = 'AI 엔진 준비 중...';
        step1.className = 'step active';
        step2.className = 'step';
        step3.className = 'step';
    }

    // ═══════════════════════════════════════
    // Generate (Streaming with Progress)
    // ═══════════════════════════════════════
    function setGeneratingState(isGenerating) {
        generateBtn.disabled = isGenerating;
        generateBtn.innerText = isGenerating ? '작성 중... ⏳' : '글 작성 시작하기 🚀';
        stopBtn.style.display = isGenerating ? 'flex' : 'none';
    }

    // Stop button
    stopBtn.addEventListener('click', () => {
        if (currentAbortController) {
            currentAbortController.abort();
            currentAbortController = null;
        }
        setGeneratingState(false);
        progressContainer.style.display = 'none';
        resultHeader.style.display = 'flex';
    });

    generateBtn.addEventListener('click', async () => {
        // Prevent double-click
        if (generateBtn.disabled) return;

        const topic = document.getElementById('topic').value.trim();
        const purpose = document.getElementById('purpose').value;
        const tone = document.getElementById('tone').value;
        const keywords = document.getElementById('keywords').value.trim();
        const engine = document.getElementById('engine').value;
        const localModel = document.getElementById('localModel').value.trim();
        const localUrl = document.getElementById('localUrl').value.trim();
        
        const geminiApiKey = geminiApiKeyInput ? geminiApiKeyInput.value.trim() : "";
        const openaiApiKey = openaiApiKeyInput ? openaiApiKeyInput.value.trim() : "";
        const customApiKey = customApiKeyInput ? customApiKeyInput.value.trim() : "";
        const customModel = customModelInput ? customModelInput.value.trim() : "";
        const customBaseUrl = customBaseUrlInput ? customBaseUrlInput.value.trim() : "";

        let selectedModel = "";
        if (engine === 'gemini') {
            selectedModel = document.getElementById('geminiModel').value;
        } else if (engine === 'openai') {
            selectedModel = document.getElementById('openaiModel').value;
        }

        if (!topic || !keywords) {
            alert('주제와 키워드를 모두 입력해주세요!');
            return;
        }

        // Create AbortController for this request
        currentAbortController = new AbortController();

        // UI Updates
        resultCard.style.display = 'block';
        resultContent.innerHTML = '';
        resultHeader.style.display = 'none';
        progressContainer.style.display = 'block';
        resetProgress();
        setGeneratingState(true);

        // Scroll to result
        resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });

        let fullText = '';

        try {
            const response = await fetch('/api/generate-stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    topic, purpose, tone, keywords, engine, 
                    model: selectedModel,
                    local_model: localModel, 
                    local_url: localUrl,
                    gemini_api_key: geminiApiKey,
                    openai_api_key: openaiApiKey,
                    custom_api_key: customApiKey,
                    custom_base_url: customBaseUrl,
                    custom_model: customModel
                }),
                signal: currentAbortController.signal,
            });

            if (!response.ok) {
                if (response.status === 422) {
                    const errData = await response.json();
                    const detail = errData.detail?.[0]?.msg || '입력값을 확인해주세요.';
                    throw new Error(`입력 검증 실패: ${detail}`);
                }
                throw new Error(`HTTP ${response.status}: 서버 응답 에러`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.type === 'stage') {
                            const stageLabels = {
                                'connecting': '🔗 AI 엔진 연결 중...',
                                'generating': '✍️ 텍스트 생성 중...',
                                'formatting': '📝 결과 포맷팅 중...',
                                'retrying': `🔄 재시도 중... (${data.attempt || 2}번째 시도)`
                            };
                            updateProgress(data.percent, stageLabels[data.stage] || data.stage);
                        }
                        
                        if (data.type === 'token') {
                            fullText += data.content;
                            try {
                                resultContent.innerHTML = marked.parse(fullText);
                            } catch (parseErr) {
                                resultContent.innerText = fullText; // fallback
                            }
                            if (data.percent) {
                                updateProgress(data.percent, '✍️ 텍스트 생성 중...');
                            }
                            resultContent.scrollTop = resultContent.scrollHeight;
                        }
                        
                        if (data.type === 'done') {
                            updateProgress(100, '✅ 작성 완료!');
                            setTimeout(() => {
                                progressContainer.style.display = 'none';
                                resultHeader.style.display = 'flex';
                            }, 800);
                        }
                        
                        if (data.type === 'error') {
                            updateProgress(0, '❌ 에러 발생');
                            progressContainer.style.display = 'none';
                            resultHeader.style.display = 'flex';
                            try {
                                resultContent.innerHTML = `<div class="error-message">${marked.parse(data.message)}</div>`;
                            } catch (parseErr) {
                                resultContent.innerHTML = `<div class="error-message"><p>${data.message}</p></div>`;
                            }
                        }
                    } catch (e) { console.warn('SSE 파싱 실패:', e); }
                }
            }

            // Final render check
            if (fullText && resultHeader.style.display !== 'flex') {
                try {
                    resultContent.innerHTML = marked.parse(fullText);
                } catch (parseErr) {
                    resultContent.innerText = fullText;
                }
                progressContainer.style.display = 'none';
                resultHeader.style.display = 'flex';
            }

        } catch (error) {
            if (error.name === 'AbortError') {
                console.info('사용자에 의해 생성이 중단되었습니다.');
                // User intentionally stopped - show partial result
                if (fullText) {
                    try { resultContent.innerHTML = marked.parse(fullText); } catch(e) { resultContent.innerText = fullText; }
                    resultHeader.style.display = 'flex';
                } else {
                    resultContent.innerHTML = '<div class="error-message"><p>⏹ 생성이 사용자에 의해 중단되었습니다.</p></div>';
                    resultHeader.style.display = 'flex';
                }
            } else {
                progressContainer.style.display = 'none';
                resultHeader.style.display = 'flex';
                resultContent.innerHTML = `<div class="error-message">
                    <p><strong>⚠️ 네트워크 에러</strong></p>
                    <p>서버 연결에 실패했습니다. 서버가 실행 중인지 확인해주세요.</p>
                    <p style="color:#64748b;font-size:0.85rem;margin-top:0.5rem;">상세: ${error.message || '알 수 없는 에러'}</p>
                </div>`;
            }
        } finally {
            setGeneratingState(false);
            currentAbortController = null;
        }
    });

    // ═══════════════════════════════════════
    // Copy to Clipboard
    // ═══════════════════════════════════════
    copyBtn.addEventListener('click', () => {
        const textToCopy = resultContent.innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {
            const originalText = copyBtn.innerText;
            copyBtn.innerText = '복사 완료! ✅';
            setTimeout(() => {
                copyBtn.innerText = originalText;
            }, 2000);
        }).catch(() => {
            // Fallback for older browsers / insecure context
            const textarea = document.createElement('textarea');
            textarea.value = textToCopy;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                copyBtn.innerText = '복사 완료! ✅';
                setTimeout(() => { copyBtn.innerText = '복사하기'; }, 2000);
            } catch (e) {
                alert('복사에 실패했습니다. 수동으로 텍스트를 선택하여 복사해주세요.');
            }
            document.body.removeChild(textarea);
        });
    });

    // ═══════════════════════════════════════
    // Keyboard Shortcuts
    // ═══════════════════════════════════════
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + Enter to generate
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            if (!generateBtn.disabled) generateBtn.click();
        }
        // Escape to stop
        if (e.key === 'Escape' && currentAbortController) {
            stopBtn.click();
        }
    });
});
