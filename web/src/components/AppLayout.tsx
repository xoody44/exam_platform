import { Button, Layout, Menu, Typography } from 'antd'
import {
  BarChartOutlined,
  DashboardOutlined,
  FileTextOutlined,
  LogoutOutlined,
  SettingOutlined,
  SwapOutlined,
  TeamOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: 'Панель' },
  { key: '/attempts', icon: <UnorderedListOutlined />, label: 'Попытки' },
  { key: '/students', icon: <TeamOutlined />, label: 'Ученики' },
  { key: '/variants', icon: <FileTextOutlined />, label: 'Варианты' },
  { key: '/conversion-tables', icon: <SwapOutlined />, label: 'Таблицы перевода' },
  { key: '/stats', icon: <BarChartOutlined />, label: 'Статистика' },
  { key: '/settings', icon: <SettingOutlined />, label: 'Настройки' },
]

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { username, logout } = useAuth()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth={64}>
        <div style={{ color: '#fff', padding: 16, textAlign: 'center', fontWeight: 600 }}>
          Экзамен · админ
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Typography.Text strong>Панель преподавателя</Typography.Text>
          <div>
            <Typography.Text style={{ marginRight: 12 }}>{username}</Typography.Text>
            <Button
              icon={<LogoutOutlined />}
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              Выйти
            </Button>
          </div>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}