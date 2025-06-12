// AI厳選エンタメコラム - Main JavaScript

class EntertainmentColumnApp {
    constructor() {
        this.currentTab = 'top5';
        this.allArticles = [];
        this.displayedArticles = 0;
        this.articlesPerPage = 12;
        this.currentFilters = {
            minScore: 0,
            sort: 'score'
        };
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.loadInitialData();
    }
    
    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });
        
        // Filter controls
        const sortSelect = document.getElementById('sortSelect');
        const minScoreFilter = document.getElementById('minScoreFilter');
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        
        if (sortSelect) {
            sortSelect.addEventListener('change', () => {
                this.currentFilters.sort = sortSelect.value;
                this.applyFilters();
            });
        }
        
        if (minScoreFilter) {
            minScoreFilter.addEventListener('input', () => {
                this.currentFilters.minScore = parseInt(minScoreFilter.value) || 0;
                this.applyFilters();
            });
        }
        
        if (loadMoreBtn) {
            loadMoreBtn.addEventListener('click', () => {
                this.loadMoreArticles();
            });
        }
    }
    
    async loadInitialData() {
        try {
            // Load meta information
            await this.loadMetaData();
            
            // Load initial tab content
            await this.loadTabContent(this.currentTab);
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            this.showError('データの読み込みに失敗しました。');
        }
    }
    
    async loadMetaData() {
        try {
            const response = await fetch('data/meta.json');
            if (!response.ok) throw new Error('Meta data not found');
            
            const meta = await response.json();
            
            // Update status bar
            document.getElementById('lastUpdated').textContent = 
                this.formatDateTime(meta.lastUpdated);
            document.getElementById('totalArticles').textContent = 
                meta.systemInfo.evaluatedArticles.toLocaleString();
                
        } catch (error) {
            console.error('Failed to load meta data:', error);
        }
    }
    
    async loadTabContent(tab) {
        switch (tab) {
            case 'top5':
                await this.loadTop5Articles();
                break;
            case 'all':
                await this.loadAllArticles();
                break;
            case 'categories':
                await this.loadCategories();
                break;
            case 'stats':
                await this.loadStatistics();
                break;
        }
    }
    
    async loadTop5Articles() {
        try {
            const response = await fetch('data/top5.json');
            if (!response.ok) throw new Error('TOP5 data not found');
            
            const data = await response.json();
            this.renderTop5Articles(data.articles);
            
        } catch (error) {
            console.error('Failed to load TOP5 articles:', error);
            this.showError('TOP5記事の読み込みに失敗しました。', 'top5-articles');
        }
    }
    
    async loadAllArticles() {
        try {
            const response = await fetch('data/articles.json');
            if (!response.ok) throw new Error('Articles data not found');
            
            const data = await response.json();
            this.allArticles = data.articles;
            this.displayedArticles = 0;
            this.applyFilters();
            
        } catch (error) {
            console.error('Failed to load all articles:', error);
            this.showError('記事の読み込みに失敗しました。', 'all-articles');
        }
    }
    
    async loadCategories() {
        try {
            const response = await fetch('data/categories.json');
            if (!response.ok) throw new Error('Categories data not found');
            
            const data = await response.json();
            this.renderCategories(data.categories);
            
        } catch (error) {
            console.error('Failed to load categories:', error);
            this.showError('カテゴリの読み込みに失敗しました。', 'categories-content');
        }
    }
    
    async loadStatistics() {
        try {
            const response = await fetch('data/statistics.json');
            if (!response.ok) throw new Error('Statistics data not found');
            
            const data = await response.json();
            this.renderStatistics(data.statistics);
            
        } catch (error) {
            console.error('Failed to load statistics:', error);
            this.showError('統計情報の読み込みに失敗しました。', 'stats-content');
        }
    }
    
    renderTop5Articles(articles) {
        const container = document.getElementById('top5-articles');
        if (!container) return;
        
        if (!articles || articles.length === 0) {
            container.innerHTML = '<div class="error">TOP5記事が見つかりませんでした。</div>';
            return;
        }
        
        container.innerHTML = articles.map((article, index) => 
            this.createArticleCard(article, index + 1)
        ).join('');
    }
    
    renderAllArticles(articles, append = false) {
        const container = document.getElementById('all-articles');
        if (!container) return;
        
        if (!articles || articles.length === 0) {
            if (!append) {
                container.innerHTML = '<div class="error">条件に一致する記事が見つかりませんでした。</div>';
            }
            return;
        }
        
        const articlesHtml = articles.map(article => 
            this.createArticleCard(article)
        ).join('');
        
        if (append) {
            container.innerHTML += articlesHtml;
        } else {
            container.innerHTML = articlesHtml;
        }
        
        // Update load more button visibility
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        if (loadMoreBtn) {
            const hasMore = this.displayedArticles < this.getFilteredArticles().length;
            loadMoreBtn.style.display = hasMore ? 'block' : 'none';
        }
    }
    
    renderCategories(categories) {
        const container = document.getElementById('categories-content');
        if (!container) return;
        
        const categoriesHtml = Object.entries(categories).map(([key, category]) => `
            <div class="category-card">
                <div class="category-header">
                    <h3 class="category-title">${category.name}</h3>
                    <p class="category-count">${category.count}件の記事</p>
                </div>
                <ul class="category-articles">
                    ${category.articles.map(article => `
                        <li class="category-article">
                            <a href="${article.url}" target="_blank" rel="noopener">
                                ${article.title}
                            </a>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `).join('');
        
        container.innerHTML = categoriesHtml;
    }
    
    renderStatistics(stats) {
        const container = document.getElementById('stats-content');
        if (!container) return;
        
        const statsHtml = `
            <div class="stat-card">
                <div class="stat-value">${stats.daily.total}</div>
                <div class="stat-label">今日の評価記事数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.daily.average_total_score?.toFixed(1) || '0'}</div>
                <div class="stat-label">今日の平均スコア</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.weekly.total}</div>
                <div class="stat-label">今週の評価記事数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.weekly.high_quality_count}</div>
                <div class="stat-label">今週の高品質記事</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.allTime.total}</div>
                <div class="stat-label">総評価記事数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.allTime.max_total_score}</div>
                <div class="stat-label">最高スコア</div>
            </div>
        `;
        
        container.innerHTML = statsHtml;
    }
    
    createArticleCard(article, rank = null) {
        const publishedDate = this.formatDate(article.published_at);
        const evaluatedDate = article.evaluated_at ? this.formatDate(article.evaluated_at) : '';
        
        return `
            <article class="article-card">
                ${rank ? `<div class="rank-badge rank-${rank}">${rank}</div>` : ''}
                ${article.thumbnail ? 
                    `<img src="${article.thumbnail}" alt="${article.title}" class="article-thumbnail" loading="lazy">` :
                    '<div class="article-thumbnail" style="background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%); display: flex; align-items: center; justify-content: center; color: #9ca3af; font-size: 0.875rem;">画像なし</div>'
                }
                <div class="article-content">
                    <div class="article-header">
                        <h3 class="article-title">${article.title}</h3>
                        <div class="article-meta">
                            <span class="article-author">👤 ${article.author}</span>
                            <span class="article-date">📅 ${publishedDate}</span>
                        </div>
                    </div>
                    ${article.ai_summary ? `<p class="article-summary">${article.ai_summary}</p>` : ''}
                    <div class="article-footer">
                        <div class="article-score">
                            <span class="score-badge">${article.total_score}点</span>
                            <span class="score-details">
                                文章:${article.scores.quality} 独自:${article.scores.originality} エンタメ:${article.scores.entertainment}
                            </span>
                        </div>
                        <a href="${article.url}" target="_blank" rel="noopener" class="article-link">
                            記事を読む →
                        </a>
                    </div>
                </div>
            </article>
        `;
    }
    
    switchTab(tab) {
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.toggle('active', button.dataset.tab === tab);
        });
        
        // Update tab panels
        document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === `${tab}-panel`);
        });
        
        this.currentTab = tab;
        
        // Load content if not already loaded
        this.loadTabContent(tab);
    }
    
    applyFilters() {
        const filteredArticles = this.getFilteredArticles();
        this.displayedArticles = 0;
        this.loadMoreArticles(filteredArticles);
    }
    
    getFilteredArticles() {
        let filtered = [...this.allArticles];
        
        // Apply minimum score filter
        if (this.currentFilters.minScore > 0) {
            filtered = filtered.filter(article => 
                article.total_score >= this.currentFilters.minScore
            );
        }
        
        // Apply sorting
        switch (this.currentFilters.sort) {
            case 'score':
                filtered.sort((a, b) => b.total_score - a.total_score);
                break;
            case 'date':
                filtered.sort((a, b) => 
                    new Date(b.published_at) - new Date(a.published_at)
                );
                break;
        }
        
        return filtered;
    }
    
    loadMoreArticles(articles = null) {
        const filteredArticles = articles || this.getFilteredArticles();
        const start = this.displayedArticles;
        const end = start + this.articlesPerPage;
        const articlesToShow = filteredArticles.slice(start, end);
        
        this.renderAllArticles(articlesToShow, start > 0);
        this.displayedArticles = end;
    }
    
    showError(message, containerId = null) {
        const errorHtml = `<div class="error">${message}</div>`;
        
        if (containerId) {
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = errorHtml;
            }
        } else {
            console.error(message);
        }
    }
    
    formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('ja-JP', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch (error) {
            return dateString;
        }
    }
    
    formatDateTime(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('ja-JP', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return dateString;
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new EntertainmentColumnApp();
});