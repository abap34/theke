import React, { useState, useEffect } from 'react';
import { settingsApi } from '../services/api';
import { toast } from '../components/ui/Toaster';

export default function Settings() {
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const fetchPrompt = async () => {
      try {
        const response = await settingsApi.getSummaryPrompt();
        setPrompt(response.prompt);
      } catch (error) {
        toast.error('エラー', '要約プロンプトの読み込みに失敗しました');
        console.error(error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchPrompt();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await settingsApi.updateSummaryPrompt(prompt);
      toast.success('成功', '要約プロンプトを更新しました');
    } catch (error) {
      toast.error('エラー', '要約プロンプトの更新に失敗しました');
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
