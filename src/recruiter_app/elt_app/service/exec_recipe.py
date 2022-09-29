import multiprocessing as mp
from recruiter_app.utilities.helpers import create_batch
from recruiter_app.elt_app.service.mongo import service_create_candidate_rating
import threading


class ExecuteRecipe:
    def __init__(self):
        self.cpu_count = mp.cpu_count()
        self.result_queue = mp.Queue()

    def check_data_in_queue(self):
        """
        Keep checking the queue, if the is any rating data then push to database,
        if exit condition (FINISHED) is received then stop the thread.
        :return:
        """
        print("service_create_candidate_rating thread is starting")
        while True:
            queue_data = self.result_queue.get()
            if queue_data == "FINISHED":
                break
            if type(queue_data[2]) in [float, int]:
                service_create_candidate_rating(queue_data[0],
                                                queue_data[1],
                                                queue_data[2])
        print("service_create_candidate_rating thread is stopped")

    def start_processes(self, recipe_list):
        """
        starts two threads :
        1. for executing the recipes with multiprocessing
        2. for database update via queue mechanism
        :param recipe_list: list of class object of the recipes
        :return:
        """
        batch_process_th = threading.Thread(target=self.execute,
                                            args=(recipe_list,))
        save_to_db_th = threading.Thread(target=self.check_data_in_queue)
        save_to_db_th.start()
        batch_process_th.start()
        for th in [batch_process_th, save_to_db_th]:
            th.join()
        print("Successfully processed a batch of candidates")

    def execute(self, data_list):
        """
        Executes the recipes with multiprocessing
        :param data_list:
        :return:
        """
        for data_batch in create_batch(data_list, batch_size=self.cpu_count,
                                       description="\nProcessing sub-batch {0}"):
            process_list = []
            for data in data_batch:
                if len(data) != 3:
                    raise Exception(f"Data - {data} is not sufficient to start the process")
                p = mp.Process(target=data[2].calculate_rating,
                               args=(self.result_queue,))
                p.start()
                process_list.append(p)
            [process.join() for process in process_list]
        self.result_queue.put("FINISHED")


