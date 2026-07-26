import IconNewChat from '@/assets/layout/newchat.svg'
import StoreImage from '@/assets/layout/store.svg'
import { useMemo } from 'react'
import { Link, useLocation } from 'react-router-dom'
import SessionHistory from '@/components/session-history'
import './nav.scss'

export function Nav() {
  const location = useLocation()
  const list = useMemo(
    () => [
      {
        key: '1',
        label: '新对话',
        icon: IconNewChat,
        href: '/',
      },
      {
        key: '2',
        label: '文档',
        icon: StoreImage,
        href: '/repository',
      },
    ],
    [],
  )

  return (
    <div className="base-layout-nav">
      <div className="base-layout-nav__buttons">
        {list.map((item) => (
          <Link
            className={`base-layout-nav__item ${location.pathname === item.href ? 'base-layout-nav__item--active' : ''}`}
            key={item.key}
            to={item.href ?? '#'}
          >
            <img src={item.icon} alt={item.label} />
            <span>{item.label}</span>
          </Link>
        ))}
      </div>
      <SessionHistory />
    </div>
  )
}
