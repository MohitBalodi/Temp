import { ArrowLeft, FileText } from 'lucide-react';
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { apiErrorMessage } from '@/api/client';
import ConfirmAndAddForm from '@/components/ConfirmAndAddForm';
import ExtractedFieldsTable from '@/components/ExtractedFieldsTable';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { useMe } from '@/hooks/useAuth';
import type { Decision } from '@/hooks/useReviews';
import {
  DECISION_LABEL,
  STATUS_LABEL,
  useAskForInfo,
  useDecide,
  usePostMessage,
  useReview,
  useReviewDocument,
} from '@/hooks/useReviews';

type Panel = 'none' | 'add' | 'not_issued' | 'ask';

function DocumentPreview({ caseId, available }: { caseId: string; available: boolean }) {
  const { data, isPending, isError } = useReviewDocument(caseId, available);

  if (!available) {
    return (
      <p className="text-sm text-muted-foreground">
        The uploaded file is no longer stored, so there is nothing to preview. The fields read from
        it are below.
      </p>
    );
  }
  if (isPending) return <p className="text-sm text-muted-foreground">Loading the document…</p>;
  if (isError || !data) {
    return <p className="text-sm text-destructive">The document could not be loaded.</p>;
  }

  return (
    <div className="space-y-2">
      {data.mime === 'application/pdf' ? (
        <iframe src={data.url} title="The uploaded document" className="h-[32rem] w-full rounded-md border" />
      ) : (
        <img
          src={data.url}
          alt="The document the verifier uploaded"
          className="max-h-[32rem] w-full rounded-md border object-contain"
        />
      )}
      <Button variant="outline" size="sm" asChild>
        <a href={data.url} target="_blank" rel="noreferrer">
          <FileText />
          Open full size
        </a>
      </Button>
    </div>
  );
}

/**
 * One case, for whoever may see it.
 *
 * The institution gets the document, the fields, its own matching record and
 * the four actions; the verifier gets the thread and whatever was answered;
 * an admin reads. The server decides all of that — `can_decide` and
 * `can_reply` come off the case — so the page never has to guess from a role.
 */
export default function RequestDetail() {
  const { id = '' } = useParams<{ id: string }>();
  const { data: user } = useMe();
  const { data: item, isPending, isError, error } = useReview(id);
  const [panel, setPanel] = useState<Panel>('none');
  const [reply, setReply] = useState('');
  const [text, setText] = useState('');
  const { toast } = useToast();

  const decide = useDecide(id);
  const askForInfo = useAskForInfo(id);
  const postMessage = usePostMessage(id);

  if (isPending) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (isError || !item) {
    return (
      <p className="text-sm text-destructive">
        {apiErrorMessage(error, 'This request could not be loaded.')}
      </p>
    );
  }

  const isInstitution = user?.role === 'institution';

  const answer = (decision: Decision, description: string) =>
    decide.mutate(decision, {
      onSuccess: () => {
        toast({ title: 'Answer recorded', description });
        setPanel('none');
        setText('');
      },
    });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Request for {item.cert_number ?? 'an unidentified certificate'}
          </h1>
          <p className="text-sm text-muted-foreground">
            {isInstitution ? `Asked by ${item.requester.email}` : `Sent to ${item.institution.name}`}{' '}
            on {new Date(item.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">
            {item.decision
              ? (DECISION_LABEL[item.decision] ?? item.decision)
              : (STATUS_LABEL[item.status] ?? item.status)}
          </Badge>
          <Button variant="outline" asChild>
            <Link to="/requests">
              <ArrowLeft />
              All requests
            </Link>
          </Button>
        </div>
      </div>

      {item.decision && (
        <Card>
          <CardContent className="space-y-1 pt-6">
            <p className="font-medium">
              {item.decision === 'not_issued'
                ? `${item.institution.name} states it did not issue this certificate.`
                : `${DECISION_LABEL[item.decision]} by ${item.institution.code}.`}
            </p>
            {item.decision_note && <p className="text-sm text-muted-foreground">“{item.decision_note}”</p>}
            <p className="text-xs text-muted-foreground">
              Answered by {item.decider?.email} on{' '}
              {item.decided_at && new Date(item.decided_at).toLocaleString()}. The original
              verification is unchanged.
            </p>
          </CardContent>
        </Card>
      )}

      {item.note && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">The verifier's note</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm">{item.note}</p>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">The document that was presented</CardTitle>
        </CardHeader>
        <CardContent>
          <DocumentPreview caseId={id} available={item.document_available} />
        </CardContent>
      </Card>

      {item.verification && <ExtractedFieldsTable verification={item.verification} />}

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            {item.registry_match ? 'Your matching record' : 'Your registry'}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {item.registry_match ? (
            <dl className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted-foreground">Number</dt>
                <dd className="font-mono">{item.registry_match.cert_number}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted-foreground">Student</dt>
                <dd>{item.registry_match.student_name}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted-foreground">Roll</dt>
                <dd className="font-mono">{item.registry_match.roll_number}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted-foreground">Programme</dt>
                <dd>{item.registry_match.programme}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted-foreground">Year</dt>
                <dd>{item.registry_match.year_of_passing}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-muted-foreground">Status</dt>
                <dd>{item.registry_match.status}</dd>
              </div>
            </dl>
          ) : (
            <p className="text-sm text-muted-foreground">
              No record in your registry matches this document. If you did issue it, "Confirm &
              add" creates the record from the values above.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Messages</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {item.messages.length === 0 && (
            <p className="text-sm text-muted-foreground">No messages yet.</p>
          )}
          {item.messages.map((message) => (
            <div key={message.id} className="space-y-1 border-l-2 pl-3">
              <p className="text-xs text-muted-foreground">
                {message.author.email} · {new Date(message.created_at).toLocaleString()}
              </p>
              <p className="text-sm">{message.body}</p>
            </div>
          ))}

          {item.can_reply && (
            <div className="space-y-2 pt-2">
              <Label htmlFor="reply">Reply</Label>
              <textarea
                id="reply"
                rows={3}
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
              <Button
                size="sm"
                disabled={!reply.trim() || postMessage.isPending}
                onClick={() =>
                  postMessage.mutate(reply.trim(), { onSuccess: () => setReply('') })
                }
              >
                {postMessage.isPending ? 'Sending…' : 'Send reply'}
              </Button>
              {postMessage.error && (
                <p className="text-sm text-destructive">{apiErrorMessage(postMessage.error)}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {item.can_decide && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Your answer</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {panel === 'none' && (
              <>
                <p className="text-sm text-muted-foreground">
                  Answering closes this request. The verifier sees your answer beside their
                  original result, which is left as it was.
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={() =>
                      answer({ decision: 'confirmed' }, 'The verifier has been told it is genuine.')
                    }
                    disabled={decide.isPending}
                  >
                    Confirm genuine
                  </Button>
                  <Button variant="outline" onClick={() => setPanel('add')}>
                    Confirm &amp; add to registry
                  </Button>
                  <Button variant="outline" onClick={() => setPanel('not_issued')}>
                    Not issued by us
                  </Button>
                  <Button variant="ghost" onClick={() => setPanel('ask')}>
                    Ask for more info
                  </Button>
                </div>
                {decide.error && (
                  <p className="text-sm text-destructive">{apiErrorMessage(decide.error)}</p>
                )}
              </>
            )}

            {panel === 'add' && (
              <ConfirmAndAddForm
                prefill={item.prefill ?? {}}
                pending={decide.isPending}
                error={decide.error}
                onSubmit={(decision) =>
                  answer(decision, 'The certificate was added to your registry and signed.')
                }
                onCancel={() => {
                  decide.reset();
                  setPanel('none');
                }}
              />
            )}

            {panel === 'not_issued' && (
              <div className="space-y-2">
                <Label htmlFor="reason">On what basis? (required)</Label>
                <textarea
                  id="reason"
                  rows={3}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="This number is not in our 2022 register and the roll number belongs to another student."
                  className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
                <p className="text-xs text-muted-foreground">
                  The verifier is shown this. It says you have no such record — not that the
                  document is forged.
                </p>
                <div className="flex gap-2">
                  <Button
                    disabled={!text.trim() || decide.isPending}
                    onClick={() =>
                      answer(
                        { decision: 'not_issued', reason: text.trim() },
                        'The verifier has been told you have no such record.',
                      )
                    }
                  >
                    {decide.isPending ? 'Saving…' : 'Record "not issued by us"'}
                  </Button>
                  <Button variant="outline" onClick={() => setPanel('none')} disabled={decide.isPending}>
                    Cancel
                  </Button>
                </div>
                {decide.error && (
                  <p className="text-sm text-destructive">{apiErrorMessage(decide.error)}</p>
                )}
              </div>
            )}

            {panel === 'ask' && (
              <div className="space-y-2">
                <Label htmlFor="ask">What do you need from the verifier?</Label>
                <textarea
                  id="ask"
                  rows={3}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Please send a clearer photo of the certificate number."
                  className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
                <div className="flex gap-2">
                  <Button
                    disabled={!text.trim() || askForInfo.isPending}
                    onClick={() =>
                      askForInfo.mutate(text.trim(), {
                        onSuccess: () => {
                          toast({
                            title: 'Question sent',
                            description: 'The request stays open until the verifier replies.',
                          });
                          setPanel('none');
                          setText('');
                        },
                      })
                    }
                  >
                    {askForInfo.isPending ? 'Sending…' : 'Ask for more info'}
                  </Button>
                  <Button variant="outline" onClick={() => setPanel('none')}>
                    Cancel
                  </Button>
                </div>
                {askForInfo.error && (
                  <p className="text-sm text-destructive">{apiErrorMessage(askForInfo.error)}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
