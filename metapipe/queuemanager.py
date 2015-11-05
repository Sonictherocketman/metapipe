""" A simple manager for a task queue.

The manager handles creating, submitting, and managing
running jobs, and can even resubmit jobs that have failed.

author: Brian Schrader
since: 2015-08-27
"""


import os, time


class Queue(object):

    def __init__(self, log_dir='/var/log/queuemanager/'):
        self.queue = []
        self.failed = []
        self.log_dir = log_dir
        self.log('', mode='w')

    def __repr__(self):
        return '<Manager: jobs=%s>' % len(self.queue)

    def log(self, message, log_file='queue.log', mode='a'):
        """ Writes to the main log file. """
        log = '{0}{1}'.format(self.log_dir, log_file)
        with open(log, mode) as f:
            f.write('%s\n' % message)

    def ready(self, job):
        """ Determines if the job is ready to be sumitted to the
        queue. It checks if the job depends on any currently
        running or queued operations.
        """
        all_complete = all(j.complete for j in self.queue
                if j.name in job.depends_on)
        none_failed = not any(True for j in self.failed
                if j.name in job.depends_on)
        return all_complete and none_failed

    def push(self, job):
        """ Push a job onto the queue. This does not submit the job. """
        self.queue.append(job)

    def submit_all(self):
        """ Submits all the given jobs in the queue and watches their
        progress as they proceed.
        """
        while True:
            if len(self.queue) == 0:
                break
            for job in self.queue:
                if job.running or job.queued:
                    pass
                elif job.complete:
                    self.log('Job %s is finished.' % job.name)
                elif job.error:
                    if job.attempts < job.retry:
                        self.log('Error: Job %s has failed, retrying (%s/%s)'
                                % (job.name, str(job.attempts), str(job.retry)))
                        job.submit()
                    else:
                        self.failed.append(job)
                        self.log('Error: Job %s has failed. Retried %s times.'
                                % (job.name, str(job.attempts)))
                elif self.ready(job):
                    self.log('Starting job %s' % job.name)
                    job.submit()
                else:
                    pass

            self.queue = filter(lambda x: x.running or x.queued or x.waiting,
                    self.queue)
            # Determine if the queue is locked.
            locked = all(True for j in self.queue
                    if any(True for f in self.failed
                        if f in j.depends_on))
            if locked:
                self.log(('The queue is locked. Please check the logs. %s')
                        % self.log_dir)
                return 2, 'Queue is locked'

            time.sleep(2)

        self.log('All jobs completed. Exiting.')
        return 0,