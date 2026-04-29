import { notFound } from "next/navigation"
import { allProjects } from "@/lib/projects"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"

export function generateStaticParams() {
  return allProjects.map((p) => ({ slug: p.slug }))
}

export default async function LabDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>
}) {
  const { slug } = await params
  const project = allProjects.find((p) => p.slug === slug)
  if (!project) notFound()

  return (
    <div className="container py-20 max-w-4xl">
      {/* ... isinya tetap sama ... */}
    </div>
  )
}
