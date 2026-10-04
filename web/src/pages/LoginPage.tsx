import { Button, Card, Form, Input, message, Typography, Alert } from 'antd'
import { LockOutlined, UserOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import axios from 'axios'
import { useState } from 'react'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onFinish = async (values: { username: string; password: string }) => {
    setError(null)
    setLoading(true)
    try {
      await login(values.username, values.password)
      message.success('Вход выполнен')
      navigate('/')
    } catch (e: unknown) {
      if (axios.isAxiosError(e)) {
        if (!e.response) {
          setError(`Сервер недоступен. Проверьте, что сервер запущен и Vite-прокси настроен.`)
        } else {
          const detail = e.response.data?.detail ?? `Ошибка ${e.response.status}`
          setError(String(detail))
        }
      } else {
        setError(String(e))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: '#f0f2f5',
      }}
    >
      <Card
        style={{ width: 420 }}
        title={<Typography.Title level={4} style={{ margin: 0 }}>Вход преподавателя</Typography.Title>}
      >
        {error && (
          <Alert
            type="error"
            message={error}
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        <Form form={form} layout="vertical" onFinish={onFinish}>
          <Form.Item name="username" label="Логин" rules={[{ required: true, message: 'Введите логин' }]}>
            <Input prefix={<UserOutlined />} autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" label="Пароль" rules={[{ required: true, message: 'Введите пароль' }]}>
            <Input.Password prefix={<LockOutlined />} autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            Войти
          </Button>
        </Form>
      </Card>
    </div>
  )
}