export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-4">
      <h1 className="text-4xl font-bold text-gray-800">404</h1>
      <p className="text-gray-600">抱歉，您访问的页面不存在。</p>
      <a href="/" className="text-blue-600 hover:underline">返回首页</a>
    </div>
  );
}
