import { Card, Col, Row, Statistic } from 'antd'
import { useEffect, useState } from 'react'
import api from '../api/client'
import type { Dashboard } from '../api/types'

export default function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null)

  useEffect(() => {
    let alive = true
    const load = async () => {
      try {
        const response = await api.get<Dashboard>('/admin/dashboard')
        if (alive) setData(response.data)
      } catch {
      }
    }
    load()
    const timer = setInterval(load, 10000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])

  return (
    <Row gutter={16}>
      <Col span={4}>
        <Card><Statistic title="Учеников" value={data?.students_count ?? 0} /></Card>
      </Col>
      <Col span={5}>
        <Card>
          <Statistic title="Идёт экзамен" value={data?.attempts_in_progress ?? 0} valueStyle={{ color: '#1677ff' }} />
        </Card>
      </Col>
      <Col span={5}>
        <Card>
          <Statistic title="Завершено" value={data?.attempts_finished ?? 0} valueStyle={{ color: '#3f8600' }} />
        </Card>
      </Col>
      <Col span={5}>
        <Card>
          <Statistic title="Прервано" value={data?.attempts_aborted ?? 0} valueStyle={{ color: '#cf1322' }} />
        </Card>
      </Col>
      <Col span={5}>
        <Card><Statistic title="Активных вариантов" value={data?.variants_active ?? 0} /></Card>
      </Col>
    </Row>
  )
}