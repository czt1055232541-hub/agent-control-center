import React from "react";

type State = { error: Error | null };

export class AppErrorBoundary extends React.Component<React.PropsWithChildren, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ACC render failure", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 p-6 text-slate-950">
        <section className="w-full max-w-xl rounded-lg border border-red-300 bg-white p-6 shadow-sm">
          <h1 className="text-lg font-semibold">控制中心页面加载失败</h1>
          <p className="mt-2 text-sm text-slate-600">后台服务和已有任务不会因此停止。可重新加载页面恢复；若问题持续，请查看浏览器控制台和 ACC 日志。</p>
          <pre className="mt-4 max-h-32 overflow-auto rounded bg-slate-100 p-3 text-xs text-red-800">{this.state.error.message}</pre>
          <button className="mt-4 rounded bg-slate-900 px-4 py-2 text-sm text-white" onClick={() => window.location.reload()}>
            重新加载
          </button>
        </section>
      </main>
    );
  }
}
