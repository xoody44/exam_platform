import { Card, Typography } from 'antd'

export default function PlaceholderPage({ title }: { title: string }) {
  return (
    <Card>
      <Typography.Title level={3}>{title}</Typography.Title>
      <Typography.Text>Страница в разработке — будет добавлена в следующем блоке.</Typography.Text>
    </Card>
  )
}