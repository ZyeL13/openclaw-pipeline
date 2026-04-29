// components/CaseStudyCard.tsx
import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"

interface CaseStudyProps {
  slug: string
  title: string
  description: string
  stack: string[]
  impact?: string
}

export default function CaseStudyCard({
  slug,
  title,
  description,
  stack,
  impact,
}: CaseStudyProps) {
  return (
    <Link href={`/lab/${slug}`}>
      <Card className="group bg-zinc-900 border-zinc-800 hover:border-cyan-500/50 transition-all overflow-hidden h-full">
        <div className="aspect-video bg-zinc-800 flex items-center justify-center text-zinc-600 text-sm font-mono">
          <span className="group-hover:text-cyan-400 transition-colors">
            [screenshot]
          </span>
        </div>
        <CardContent className="p-5 space-y-3">
          <h3 className="text-lg font-semibold group-hover:text-cyan-400 transition-colors">
            {title}
          </h3>
          <p className="text-sm text-zinc-400 line-clamp-2">{description}</p>
          <div className="flex flex-wrap gap-1.5">
            {stack.map((tech) => (
              <Badge
                key={tech}
                variant="secondary"
                className="bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
              >
                {tech}
              </Badge>
            ))}
          </div>
        </CardContent>
        {impact && (
          <CardFooter className="px-5 pb-5 pt-0 text-xs text-zinc-500 border-t border-zinc-800 mt-2 pt-3">
            {impact}
          </CardFooter>
        )}
      </Card>
    </Link>
  )
}
