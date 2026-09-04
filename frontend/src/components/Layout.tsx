import { Outlet, NavLink } from 'react-router-dom';
import { Search, BookOpen, Database } from 'lucide-react';
import clsx from 'clsx';
import type { CapabilitiesResponse } from '../types';

export default function Layout({ capabilities }: { capabilities: CapabilitiesResponse }) {
  const navItems = [
    { to: '/search', icon: Search, label: '跨文献关联检索' },
    { to: '/sources', icon: BookOpen, label: '文献来源' },
  ];

  const providerStatus = capabilities.providers.every(p => p.available) ? 'available' : 'degraded';

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-wrap justify-between h-auto sm:h-16 py-2 sm:py-0">
            <div className="flex flex-col sm:flex-row items-center w-full sm:w-auto">
              <div className="flex-shrink-0 flex items-center">
                <Database className="h-8 w-8 text-blue-600" aria-hidden="true" />
                <span className="ml-2 text-xl font-bold text-gray-900">机图索隐</span>
              </div>
              <nav className="mt-4 sm:mt-0 sm:ml-6 flex space-x-4 sm:space-x-8 w-full sm:w-auto overflow-x-auto" aria-label="Main Navigation">
                {navItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      clsx(
                        'inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium whitespace-nowrap',
                        isActive
                          ? 'border-blue-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      )
                    }
                  >
                    <item.icon className="mr-2 h-4 w-4" aria-hidden="true" />
                    {item.label}
                  </NavLink>
                ))}
              </nav>
            </div>
            <div className="flex items-center text-xs text-gray-400 mt-2 sm:mt-0 w-full sm:w-auto justify-end">
               API: {providerStatus === 'available' ? <span className="text-green-500 ml-1">可用</span> : <span className="text-yellow-500 ml-1">部分降级</span>}
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
