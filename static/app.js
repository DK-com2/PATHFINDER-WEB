class PathfinderApp {
    constructor() {
        this.token = localStorage.getItem('token');
        this.user = null;
        this.currentPage = 'login';
        this.timelineData = [];
        this.summary = null;

        this.init();
    }

    async init() {
        if (this.token) {
            const isValid = await this.verifyToken();
            if (isValid) {
                await this.loadUserProfile();
                this.showDashboard();
            } else {
                this.showLogin();
            }
        } else {
            this.showLogin();
        }
    }

    showLoading() {
        document.getElementById('loading-overlay').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    }

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        const bgColor = type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-500' : 'bg-blue-500';

        toast.className = `${bgColor} text-white px-6 py-3 rounded-lg shadow-lg mb-3 fade-in`;
        toast.textContent = message;

        document.getElementById('toast-container').appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    async makeRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            }
        };

        if (this.token) {
            defaultOptions.headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(url, { ...defaultOptions, ...options });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'リクエストに失敗しました');
        }

        return response.json();
    }

    async verifyToken() {
        try {
            await this.makeRequest('/api/auth/verify');
            return true;
        } catch (error) {
            localStorage.removeItem('token');
            this.token = null;
            return false;
        }
    }

    async loadUserProfile() {
        try {
            this.user = await this.makeRequest('/api/auth/profile');
        } catch (error) {
            console.error('Failed to load user profile:', error);
        }
    }

    showLogin() {
        this.currentPage = 'login';
        const app = document.getElementById('app');

        app.innerHTML = `
            <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 px-4 py-6">
                <div class="w-full max-w-md space-y-6 p-6 sm:p-8 bg-white rounded-xl shadow-lg fade-in">
                    <div class="text-center">
                        <div class="flex justify-between items-start mb-4">
                            <div></div>
                            <div>
                                <h2 class="text-2xl sm:text-3xl font-extrabold text-gray-900">
                                    🌐 Pathfinder Web
                                </h2>
                                <p class="mt-2 text-sm text-gray-600">
                                    アカウントにログインしてください
                                </p>
                            </div>
                            <div class="mt-6">
                                <a href="/static/developer.html" 
                                   class="text-xs text-gray-400 hover:text-gray-600 transition-colors">
                                    🔧
                                </a>
                            </div>
                        </div>
                    </div>
                    
                    <form id="login-form" class="mt-8 space-y-6">
                        <div class="space-y-4">
                            <div>
                                <label for="email" class="block text-sm font-medium text-gray-700">
                                    メールアドレス
                                </label>
                                <input id="email" name="email" type="email" required
                                    class="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                                    placeholder="example@email.com">
                            </div>
                            
                            <div>
                                <label for="password" class="block text-sm font-medium text-gray-700">
                                    パスワード
                                </label>
                                <input id="password" name="password" type="password" required
                                    class="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                                    placeholder="パスワード">
                            </div>
                        </div>
                        
                        <div class="space-y-3">
                            <button type="submit" 
                                class="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors touch-manipulation">
                                ログイン
                            </button>
                            
                            <button type="button" id="signup-btn"
                                class="group relative w-full flex justify-center py-3 px-4 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors touch-manipulation">
                                新規アカウント作成
                            </button>
                            
                            <button type="button" id="demo-login-btn"
                                class="group relative w-full flex justify-center py-3 px-4 border border-gray-300 text-sm font-medium rounded-md text-orange-700 bg-orange-50 hover:bg-orange-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 transition-colors touch-manipulation">
                                デモアカウントでログイン
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.getElementById('login-form').addEventListener('submit', this.handleLogin.bind(this));
        document.getElementById('signup-btn').addEventListener('click', this.handleSignupClick.bind(this));
        document.getElementById('demo-login-btn').addEventListener('click', this.handleDemoLogin.bind(this));
    }

    async handleLogin(e) {
        e.preventDefault();

        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        this.showLoading();

        try {
            const response = await this.makeRequest('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ email, password })
            });

            this.token = response.access_token;
            localStorage.setItem('token', this.token);

            await this.loadUserProfile();
            this.showToast('ログインに成功しました', 'success');
            this.showDashboard();
        } catch (error) {
            this.showToast(`ログインに失敗しました: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    handleSignupClick() {
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        if (!email || !password) {
            this.showToast('メールアドレスとパスワードを入力してください', 'error');
            return;
        }

        this.handleSignup(email, password);
    }

    async handleSignup(email, password) {
        this.showLoading();

        try {
            const response = await this.makeRequest('/api/auth/signup', {
                method: 'POST',
                body: JSON.stringify({ email, password })
            });

            this.token = response.access_token;
            localStorage.setItem('token', this.token);

            await this.loadUserProfile();
            this.showToast('アカウント作成に成功しました', 'success');
            this.showDashboard();
        } catch (error) {
            this.showToast(`アカウント作成に失敗しました: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async handleDemoLogin() {
        this.showLoading();

        try {
            const response = await this.makeRequest('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({
                    email: 'iowlb3e5aq@sute.jp',
                    password: '000000'
                })
            });

            this.token = response.access_token;
            localStorage.setItem('token', this.token);

            await this.loadUserProfile();
            this.showToast('デモアカウントでログインしました', 'success');
            this.showDashboard();
        } catch (error) {
            this.showToast(`デモログインに失敗しました: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    showDashboard() {
        this.currentPage = 'dashboard';
        const app = document.getElementById('app');

        app.innerHTML = `
            <div class="min-h-screen bg-gray-50">
                <!-- ヘッダー -->
                <nav class="bg-white shadow-lg">
                    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div class="flex justify-between h-16">
                            <div class="flex items-center">
                                <h1 class="text-lg sm:text-xl font-semibold text-gray-900">
                                    🌐 Pathfinder Web
                                </h1>
                            </div>
                            
                            <div class="flex items-center space-x-2 sm:space-x-4">
                                <span class="text-xs sm:text-sm text-gray-600 hidden sm:inline">
                                    👤 ${this.user?.email || 'ユーザー'}
                                </span>
                                <button id="logout-btn" 
                                    class="bg-red-600 hover:bg-red-700 text-white px-3 py-2 sm:px-4 rounded-md text-xs sm:text-sm font-medium transition-colors touch-manipulation">
                                    ログアウト
                                </button>
                            </div>
                        </div>
                    </div>
                </nav>
                
                <!-- メインコンテンツ -->
                <main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
                    <div class="fade-in">
                        <!-- ユーザー情報セクション -->
                        <div class="bg-white overflow-hidden shadow rounded-lg mb-6">
                            <div class="px-4 py-5 sm:p-6">
                                <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
                                    👤 ユーザー情報
                                </h3>
                                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <p class="text-sm text-gray-600">メールアドレス</p>
                                        <p class="text-lg font-medium text-gray-900">${this.user?.email || 'N/A'}</p>
                                    </div>
                                    <div>
                                        <p class="text-sm text-gray-600">ユーザー名</p>
                                        <div id="username-section">
                                            ${this.user?.username ?
                `<p class="text-lg font-medium text-gray-900">${this.user.username}</p>` :
                `<div class="flex items-center space-x-2">
                                                    <input id="username-input" type="text" placeholder="ユーザー名を入力" 
                                                        class="border border-gray-300 rounded px-3 py-1 text-sm">
                                                    <button id="set-username-btn" 
                                                        class="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm">
                                                        設定
                                                    </button>
                                                </div>`
            }
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- データサマリーセクション -->
                        <div class="bg-white overflow-hidden shadow rounded-lg mb-6">
                            <div class="px-4 py-5 sm:p-6">
                                <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
                                    📊 データサマリー
                                </h3>
                                <div id="summary-content" class="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3">
                                    <button id="load-summary-btn" 
                                        class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-md text-sm font-medium touch-manipulation w-full sm:w-auto">
                                        📥 サマリーを読み込む
                                    </button>
                                    <a href="/static/map.html" 
                                        class="bg-green-600 hover:bg-green-700 text-white px-4 py-3 rounded-md text-sm font-medium inline-block text-center touch-manipulation w-full sm:w-auto">
                                        🗺️ 地図で表示
                                    </a>
                                </div>
                            </div>
                        </div>
                        
                        <!-- タイムラインアップロードセクション -->
                        <div class="bg-white overflow-hidden shadow rounded-lg mb-6">
                            <div class="px-4 py-5 sm:p-6">
                                <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
                                    📤 タイムラインデータアップロード
                                </h3>
                                <div class="space-y-4">
                                    <p class="text-gray-600">
                                        Google TimelineのJSONファイルをアップロードして、位置データを地図で可視化できます。
                                    </p>
                                    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between p-4 bg-blue-50 rounded-lg space-y-3 sm:space-y-0">
                                        <div>
                                            <h4 class="font-medium text-blue-900">Google Timeline データをインポート</h4>
                                            <p class="text-sm text-blue-700 mt-1">エクスポート方法の説明とファイルアップロード機能</p>
                                        </div>
                                        <a href="/static/upload.html" 
                                            class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-md text-sm font-medium transition-colors inline-block text-center touch-manipulation">
                                            📤 アップロードページへ
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
        `;

        // イベントリスナーを設定
        this.setupDashboardEventListeners();
    }

    setupDashboardEventListeners() {
        document.getElementById('logout-btn').addEventListener('click', this.handleLogout.bind(this));
        document.getElementById('load-summary-btn').addEventListener('click', this.loadSummary.bind(this));


        const setUsernameBtn = document.getElementById('set-username-btn');
        if (setUsernameBtn) {
            setUsernameBtn.addEventListener('click', this.setUsername.bind(this));
        }

        // アップロード関連のイベントリスナーは upload.html で処理
    }

    async handleLogout() {
        this.showLoading();

        try {
            await this.makeRequest('/api/auth/logout', { method: 'POST' });
            localStorage.removeItem('token');
            this.token = null;
            this.user = null;
            this.showToast('ログアウトしました', 'success');
            this.showLogin();
        } catch (error) {
            this.showToast(`ログアウトに失敗しました: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async setUsername() {
        const username = document.getElementById('username-input').value.trim();
        if (!username) {
            this.showToast('ユーザー名を入力してください', 'error');
            return;
        }

        this.showLoading();

        try {
            await this.makeRequest('/api/auth/set-username', {
                method: 'POST',
                body: JSON.stringify({ username })
            });

            this.user.username = username;
            this.showToast('ユーザー名を設定しました', 'success');
            this.showDashboard(); // リフレッシュ
        } catch (error) {
            this.showToast(`ユーザー名の設定に失敗しました: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async loadSummary() {
        this.showLoading();

        try {
            const response = await this.makeRequest('/api/timeline/summary');
            this.summary = response.summary;
            this.displaySummary();
        } catch (error) {
            this.showToast(`サマリーの読み込みに失敗しました: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    displaySummary() {
        const summaryContent = document.getElementById('summary-content');

        if (!this.summary || this.summary.total_records === 0) {
            summaryContent.innerHTML = `
                <p class="text-gray-500">データが見つかりませんでした。ユーザー名を設定してデータを確認してください。</p>
            `;
            return;
        }

        summaryContent.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div class="bg-blue-50 p-4 rounded-lg">
                    <p class="text-sm text-blue-600 font-medium">総レコード数</p>
                    <p class="text-2xl font-bold text-blue-900">${this.summary.total_records.toLocaleString()}</p>
                </div>
                <div class="bg-green-50 p-4 rounded-lg">
                    <p class="text-sm text-green-600 font-medium">ユーザー名</p>
                    <p class="text-2xl font-bold text-green-900">${this.summary.username}</p>
                </div>
                <div class="bg-purple-50 p-4 rounded-lg">
                    <p class="text-sm text-purple-600 font-medium">データ期間</p>
                    <p class="text-sm font-medium text-purple-900">
                        ${this.summary.date_range?.start ? new Date(this.summary.date_range.start).toLocaleDateString('ja-JP') : 'N/A'} 〜 
                        ${this.summary.date_range?.end ? new Date(this.summary.date_range.end).toLocaleDateString('ja-JP') : 'N/A'}
                    </p>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <h4 class="font-medium text-gray-900 mb-2">データタイプ分布</h4>
                    <div class="space-y-1">
                        ${Object.entries(this.summary.type_distribution || {}).map(([type, count]) => `
                            <div class="flex justify-between">
                                <span class="text-sm text-gray-600">${type}</span>
                                <span class="text-sm font-medium">${count.toLocaleString()}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div>
                    <h4 class="font-medium text-gray-900 mb-2">トップアクティビティ</h4>
                    <div class="space-y-1">
                        ${Object.entries(this.summary.top_activity_types || {}).slice(0, 5).map(([type, count]) => `
                            <div class="flex justify-between">
                                <span class="text-sm text-gray-600">${type}</span>
                                <span class="text-sm font-medium">${count.toLocaleString()}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
    }

    async loadTimelineData() {
        this.showLoading();

        try {
            const response = await this.makeRequest('/api/timeline/data?limit=100');
            this.timelineData = response.data;
            this.displayTimelineData();
        } catch (error) {
            this.showToast(`データの読み込みに失敗しました: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    displayTimelineData() {
        const timelineContent = document.getElementById('timeline-content');

        if (!this.timelineData || this.timelineData.length === 0) {
            timelineContent.innerHTML = `
                <p class="text-gray-500 text-center py-8">データが見つかりませんでした。</p>
            `;
            return;
        }

        timelineContent.innerHTML = `
            <div class="mb-4">
                <p class="text-sm text-gray-600">${this.timelineData.length} 件のデータ（最新100件）</p>
            </div>
            
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                タイプ
                            </th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                開始時刻
                            </th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                位置
                            </th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                詳細
                            </th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                        ${this.timelineData.map(item => `
                            <tr class="hover:bg-gray-50">
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${item.type === 'activitySegment' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
            }">
                                        ${item.type}
                                    </span>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                    ${item.start_time ? new Date(item.start_time).toLocaleString('ja-JP') : 'N/A'}
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                    ${item.latitude && item.longitude ?
                `${item.latitude.toFixed(4)}, ${item.longitude.toFixed(4)}` : 'N/A'}
                                </td>
                                <td class="px-6 py-4 text-sm text-gray-500">
                                    ${item.activity_type || item.visit_semantictype || 'N/A'}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        const uploadBtn = document.getElementById('upload-btn');
        const uploadResult = document.getElementById('upload-result');

        // 結果をクリア
        uploadResult.classList.add('hidden');

        if (file) {
            // ファイルサイズチェック（100MB）
            const maxSize = 100 * 1024 * 1024;
            if (file.size > maxSize) {
                this.showToast(`ファイルサイズが大きすぎます: ${(file.size / 1024 / 1024).toFixed(1)}MB > 100MB`, 'error');
                uploadBtn.disabled = true;
                return;
            }

            // ファイル形式チェック
            if (!file.name.toLowerCase().endsWith('.json')) {
                this.showToast('JSONファイルを選択してください', 'error');
                uploadBtn.disabled = true;
                return;
            }

            uploadBtn.disabled = false;
        } else {
            uploadBtn.disabled = true;
        }
    }

    async handleFileUpload() {
        const fileInput = document.getElementById('timeline-file');
        const file = fileInput.files[0];

        if (!file) {
            this.showToast('ファイルを選択してください', 'error');
            return;
        }

        const uploadProgress = document.getElementById('upload-progress');
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');
        const uploadResult = document.getElementById('upload-result');
        const uploadBtn = document.getElementById('upload-btn');

        try {
            // UI状態を更新
            uploadBtn.disabled = true;
            uploadProgress.classList.remove('hidden');
            uploadResult.classList.add('hidden');
            progressBar.style.width = '0%';
            progressText.textContent = '⚡ 高速アップロード中...';

            // FormDataを作成
            const formData = new FormData();
            formData.append('file', file);

            // アップロード実行（タイムアウト設定）
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 1800000); // 30分タイムアウト

            const response = await fetch('/api/timeline/upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`
                },
                body: formData,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            // プログレスバーを100%に
            progressBar.style.width = '100%';
            progressText.textContent = '⚡ 高速処理中...';

            // 大きなファイルの場合は追加の待機メッセージ
            if (file.size > 10 * 1024 * 1024) { // 10MB以上
                setTimeout(() => {
                    if (progressText.textContent.includes('処理中...')) {
                        progressText.textContent = '⚡ 大量データを高速処理中です。お待ちください...';
                    }
                }, 5000);
            }

            const result = await response.json();

            if (response.ok) {
                this.displayUploadSuccess(result);
                this.showToast('高速アップロードが完了しました', 'success');

                // サマリーを自動更新
                await this.loadSummary();
            } else {
                this.displayUploadError(result);
                this.showToast(`アップロードに失敗しました: ${result.detail}`, 'error');
            }

        } catch (error) {
            this.displayUploadError({ detail: error.message });
            this.showToast(`アップロードエラー: ${error.message}`, 'error');
        } finally {
            // UI状態をリセット
            uploadProgress.classList.add('hidden');
            uploadBtn.disabled = false;
            fileInput.value = '';
        }
    }

    displayUploadSuccess(result) {
        const uploadResult = document.getElementById('upload-result');

        uploadResult.innerHTML = `
            <div class="bg-green-50 border border-green-200 rounded-md p-4">
                <div class="flex items-start">
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-green-800">
                            ✅ アップロード成功
                        </h3>
                        <div class="mt-2 text-sm text-green-700">
                            <p><strong>ファイル名:</strong> ${result.filename}</p>
                            <p><strong>処理レコード数:</strong> ${result.total_records.toLocaleString()}</p>
                            <p><strong>保存レコード数:</strong> ${result.saved_records.toLocaleString()}</p>
                            ${result.validation_summary && result.validation_summary.warning_count > 0 ?
                `<p class="text-yellow-600"><strong>警告:</strong> ${result.validation_summary.warning_count}件</p>` : ''
            }
                        </div>
                    </div>
                </div>
            </div>
        `;

        uploadResult.classList.remove('hidden');
    }

    displayUploadError(result) {
        const uploadResult = document.getElementById('upload-result');

        uploadResult.innerHTML = `
            <div class="bg-red-50 border border-red-200 rounded-md p-4">
                <div class="flex items-start">
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800">
                            ❌ アップロード失敗
                        </h3>
                        <div class="mt-2 text-sm text-red-700">
                            <p>${result.detail || 'アップロード処理中にエラーが発生しました'}</p>
                            ${result.validation_summary && result.validation_summary.errors ?
                `<div class="mt-2">
                                    <p><strong>検証エラー:</strong></p>
                                    <ul class="list-disc list-inside ml-2">
                                        ${result.validation_summary.errors.map(error => `<li>${error}</li>`).join('')}
                                    </ul>
                                </div>` : ''
            }
                        </div>
                    </div>
                </div>
            </div>
        `;

        uploadResult.classList.remove('hidden');
    }
}

// アプリケーションを起動
document.addEventListener('DOMContentLoaded', () => {
    new PathfinderApp();
});