import React, { useState, useEffect } from 'react';
import { settingsApi } from '../services/api';
import { toast } from '../components/ui/Toaster';

export default function Settings() {
  const [prompt, setPrompt] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const [promptResponse, modelResponse] = await Promise.all([
          settingsApi.getSummaryPrompt(),
          settingsApi.getModelSetting()
        ]);

        setPrompt(promptResponse.prompt);
        setSelectedModel(modelResponse.model);
      } catch (error) {
        toast.error('エラー', '設定の読み込みに失敗しました');
        console.error(error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await Promise.all([
        settingsApi.updateSummaryPrompt(prompt),
        settingsApi.updateModelSetting(selectedModel)
      ]);
      toast.success('成功', '設定を更新しました');
    } catch (error) {
      toast.error('エラー', '設定の更新に失敗しました');
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">設定</h1>
        <p className="text-gray-600">アプリケーションの設定を管理します</p>
      </div>

      <div className="space-y-6">
        {/* Model Selection */}
        <div className="card p-6">
          <div className="mb-6">
            <label htmlFor="model-input" className="label">
              要約生成モデル
            </label>
            <p className="text-sm text-gray-500 mb-3">
              論文の要約生成に使用するAnthropicのモデルIDを入力します。
              <a
                href="https://docs.claude.com/en/docs/about-claude/models"
                target="_blank"
                rel="noopener noreferrer"
                className="ml-2 text-primary-600 hover:text-primary-700 underline"
              >
                利用可能なモデル一覧を確認
              </a>
            </p>
            <input
              id="model-input"
              type="text"
              className="input font-mono text-sm"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              placeholder="例: claude-sonnet-4-5-20250929"
            />
            <div className="mt-3 p-4 bg-blue-50 border border-blue-200 rounded-md">
              <h4 className="text-sm font-semibold text-blue-900 mb-2">推奨モデル（2025年現在）</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li><code className="bg-blue-100 px-1.5 py-0.5 rounded">claude-sonnet-4-5-20250929</code> - 最新の高性能モデル（推奨）</li>
                <li><code className="bg-blue-100 px-1.5 py-0.5 rounded">claude-haiku-4-5-20251001</code> - 高速で経済的</li>
                <li><code className="bg-blue-100 px-1.5 py-0.5 rounded">claude-opus-4-1-20250805</code> - 最高性能</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Summary Prompt */}
        <div className="card p-6">
          <div className="mb-6">
            <label htmlFor="summary-prompt" className="label">
              要約プロンプト
            </label>
            <p className="text-sm text-gray-500 mb-3">
              論文の要約を生成する際に使用されるプロンプトです。必要に応じてカスタマイズできます。
            </p>
            <textarea
              id="summary-prompt"
              rows={12}
              className="input font-mono text-sm"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="要約生成用のプロンプトを入力してください..."
            />
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="btn btn-primary btn-md"
          >
            {isSaving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
}
