import { useEffect, useState } from 'react'
import { Card, Col, Progress, Row, Statistic, Table, Typography } from 'antd'
import api from '../api/client'
import type { Stats, StatsTask } from '../api/types'

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    api.get<Stats>('/admin/stats').then((r) => setStats(r.data)).catch(() => {})
  }, [])

  if (!stats) return <Card><Typography.Text>Загрузка…</Typography.Text></Card>

  const o = stats.overview
  const fmt = (v: number | null) => (v == null ? '—' : v.toFixed(1))

  return (
    <>
      <Card title="Обзор по завершённым попыткам">
        <Row gutter={16}>
          <Col span={4}><Statistic title="Попыток" value={o.attempts_count} /></Col>
          <Col span={5}><Statistic title="Средний первичный" value={fmt(o.avg_primary)} /></Col>
          <Col span={5}><Statistic title="Средний тестовый" value={fmt(o.avg_test)} /></Col>
          <Col span={5}>
            <Statistic
              title="Первичный мин / макс"
              value={o.min_primary ?? '—'}
              suffix={o.max_primary != null ? `/ ${o.max_primary}` : undefined}
            />
          </Col>
          <Col span={5}>
            <Statistic
              title="Тестовый мин / макс"
              value={o.min_test ?? '—'}
              suffix={o.max_test != null ? `/ ${o.max_test}` : undefined}
            />
          </Col>
        </Row>
      </Card>

      <Card title="Сложность заданий (самые сложные сверху)" style={{ marginTop: 16 }}>
        <Table<StatsTask>
          rowKey="task_number"
          pagination={false}
          dataSource={stats.tasks}
          columns={[
            { title: '№', dataIndex: 'task_number', width: 60 },
            { title: 'Задание', dataIndex: 'title' },
            { title: 'Макс. балл', dataIndex: 'max_score', width: 100 },
            { title: 'Средний балл', dataIndex: 'avg_score', width: 120 },
            {
              title: 'Процент выполнения',
              dataIndex: 'completion_percent',
              width: 260,
              render: (v: number) => (
                <Progress
                  percent={v}
                  size="small"
                  status={v < 40 ? 'exception' : v < 70 ? 'normal' : 'success'}
                />
              ),
            },
          ]}
        />
      </Card>
    </>
  )
}